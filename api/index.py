import os
import tempfile
import uuid
import yaml
import json
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Adjust path to import from root
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.workflow import CeaseGuardWorkflow
from tools.db import get_connection, initialize_sqlite, initialize_postgres
from tools.rag_service import RAGService

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Ensure DB is initialized at app startup
db_type = config.get("datastore", {}).get("type", "sqlite")
if db_type == "sqlite":
    sqlite_path = config.get("datastore", {}).get("sqlite_path", "data/cease_records.db")
    if not os.path.isabs(sqlite_path):
        sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), sqlite_path)
        config["datastore"]["sqlite_path"] = sqlite_path
    initialize_sqlite(sqlite_path)
elif db_type == "postgres":
    postgres_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or config.get("datastore", {}).get("postgres_url")
    if postgres_url:
        initialize_postgres(postgres_url)

app = FastAPI(title="CeaseGuard API Backend", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReviewDecision(BaseModel):
    decision: str  # CEASE, IRRELEVANT, DEFER
    note: Optional[str] = None
    operator_id: Optional[str] = "web-operator"

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.1.0"}

@app.get("/api/metrics")
def get_metrics():
    try:
        conn = get_connection(config)
        # Cease requests count
        cur = conn.execute("SELECT COUNT(*) FROM cease_requests")
        cease_count = cur.fetchone()[0]
        
        # Archive logs count
        cur = conn.execute("SELECT COUNT(*) FROM archive_logs")
        archive_count = cur.fetchone()[0]
        
        # Deferred requests count
        cur = conn.execute("SELECT COUNT(*) FROM deferred_requests")
        deferred_count = cur.fetchone()[0]
        
        # Pending reviews count
        cur = conn.execute("""
            SELECT COUNT(DISTINCT document_id) 
            FROM audit_logs a 
            WHERE stage = 'ROUTED' AND routing_destination = 'needs_review' 
              AND NOT EXISTS (
                SELECT 1 FROM audit_logs c 
                WHERE c.document_id = a.document_id AND c.stage = 'COMPLETED'
              )
        """)
        pending_count = cur.fetchone()[0]
        
        # Total cases processed
        cur = conn.execute("SELECT COUNT(DISTINCT document_id) FROM audit_logs WHERE stage = 'RECEIVED'")
        total_processed = cur.fetchone()[0]
        
        return {
            "total_processed": total_processed,
            "cease_count": cease_count,
            "archive_count": archive_count,
            "deferred_count": deferred_count,
            "pending_reviews": pending_count
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/reviews")
def get_reviews():
    try:
        conn = get_connection(config)
        cur = conn.execute("""
            SELECT entry_id, document_id, filename, timestamp, stage, classification, confidence, citation, language, edge_case_flag, agent_trace, metadata
            FROM audit_logs a
            WHERE stage = 'ROUTED' AND routing_destination = 'needs_review'
              AND NOT EXISTS (
                SELECT 1 FROM audit_logs c
                WHERE c.document_id = a.document_id AND c.stage = 'COMPLETED'
              )
            ORDER BY timestamp DESC
        """)
        rows = cur.fetchall()
        reviews = []
        for r in rows:
            metadata_dict = {}
            if r[11]:
                try:
                    metadata_dict = json.loads(r[11])
                except Exception:
                    pass
            
            agent_trace = []
            if r[10]:
                try:
                    agent_trace = json.loads(r[10])
                except Exception:
                    pass

            reviews.append({
                "entry_id": r[0],
                "document_id": r[1],
                "filename": r[2],
                "timestamp": r[3],
                "stage": r[4],
                "classification": {
                    "label": r[5],
                    "confidence": r[6],
                    "citation": r[7],
                    "edge_case_flag": bool(r[9])
                },
                "language": {
                    "language": r[8],
                    "confidence": 1.0
                },
                "agent_trace": agent_trace,
                "text": metadata_dict.get("text", ""),
                "pdf_path": metadata_dict.get("pdf_path", "")
            })
        return reviews
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/reviews/{document_id}")
def submit_review(document_id: str, payload: ReviewDecision):
    try:
        conn = get_connection(config)
        # Find the pending review in audit_logs to reconstruct workflow state
        cur = conn.execute("""
            SELECT filename, classification, confidence, citation, language, edge_case_flag, agent_trace, metadata
            FROM audit_logs a
            WHERE document_id = ? AND stage = 'ROUTED' AND routing_destination = 'needs_review'
            ORDER BY id DESC LIMIT 1
        """, (document_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pending review not found for document ID")

        metadata_dict = {}
        if row[7]:
            try:
                metadata_dict = json.loads(row[7])
            except Exception:
                pass
        
        agent_trace = []
        if row[6]:
            try:
                agent_trace = json.loads(row[6])
            except Exception:
                pass

        # Reconstruct workflow state
        state = {
            "document_id": document_id,
            "filename": row[0],
            "pdf_path": metadata_dict.get("pdf_path", ""),
            "text": metadata_dict.get("text", ""),
            "classification": {
                "label": row[1],
                "confidence": row[2],
                "citation": row[3],
                "edge_case_flag": bool(row[5]),
                "reasoning": "Restored from review queue"
            },
            "language": {
                "language": row[4],
                "confidence": 1.0
            },
            "current_stage": "ROUTE",
            "human_decision": {
                "decision": payload.decision,
                "decided_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "operator_id": payload.operator_id or "web-operator",
                "note": payload.note
            },
            "trace": agent_trace
        }

        # Run stateful workflow
        workflow = CeaseGuardWorkflow(config)
        res = workflow.run(state)

        if res.get("current_stage") == "COMPLETED":
            return {"status": "success", "route_result": res.get("route_result")}
        else:
            return {"status": "error", "message": res.get("error", "Workflow failed to complete.")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/reviews/{document_id}/similarity")
def get_similar_reviews(document_id: str, limit: int = Query(3, ge=1, le=10)):
    try:
        conn = get_connection(config)
        # Find the text of the document in audit_logs metadata
        cur = conn.execute("""
            SELECT metadata FROM audit_logs
            WHERE document_id = ? AND stage = 'ROUTED' AND routing_destination = 'needs_review'
            ORDER BY id DESC LIMIT 1
        """, (document_id,))
        row = cur.fetchone()
        
        # If not found under routed, try finding under RECEIVED
        if not row:
            cur = conn.execute("""
                SELECT metadata FROM audit_logs
                WHERE document_id = ? AND stage = 'RECEIVED'
                ORDER BY id DESC LIMIT 1
            """, (document_id,))
            row = cur.fetchone()

        if not row or not row[0]:
            return []

        try:
            metadata_dict = json.loads(row[0])
            text = metadata_dict.get("text", "")
        except Exception:
            return []

        if not text:
            return []

        # Find similar documents
        rag = RAGService(config)
        similar = rag.find_similar(text, limit=limit)
        return similar
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...)):
    temp_path = None
    try:
        # Create temp folder if not exists
        os.makedirs("/tmp", exist_ok=True)
        # Save uploaded file
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir="/tmp")
        os.close(fd)
        
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Initialize workflow state
        state = {
            "pdf_path": temp_path,
            "filename": file.filename,
            "current_stage": "INGEST"
        }

        # Run stateful workflow
        workflow = CeaseGuardWorkflow(config)
        res = workflow.run(state)

        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

        if res.get("current_stage") == "COMPLETED":
            return {
                "status": "completed",
                "document_id": res.get("document_id"),
                "classification": res.get("classification"),
                "route_result": res.get("route_result")
            }
        elif res.get("current_stage") == "ESCALATED":
            return {
                "status": "needs_review",
                "document_id": res.get("document_id"),
                "classification": res.get("classification"),
                "route_result": res.get("route_result")
            }
        else:
            raise HTTPException(status_code=500, detail=res.get("error", "Workflow execution failed"))
            
    except Exception as exc:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/ingest/sample")
def ingest_sample_document(payload: Dict[str, str]):
    sample_name = payload.get("sample_name")
    if not sample_name:
        raise HTTPException(status_code=400, detail="Missing sample_name parameter")
        
    samples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples")
    sample_path = os.path.join(samples_dir, sample_name)
    
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail=f"Sample document not found: {sample_name}")
        
    # Copy to temp file to simulate ingest
    suffix = os.path.splitext(sample_name)[1]
    # Check if /tmp exists, else let tempfile handle fallback
    tmp_dir = "/tmp" if os.path.exists("/tmp") else None
    fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=tmp_dir)
    os.close(fd)
    
    try:
        shutil.copyfile(sample_path, temp_path)
        
        state = {
            "pdf_path": temp_path,
            "filename": sample_name,
            "current_stage": "INGEST"
        }
        
        workflow = CeaseGuardWorkflow(config)
        res = workflow.run(state)
        
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
                
        if res.get("current_stage") == "COMPLETED":
            return {
                "status": "completed",
                "document_id": res.get("document_id"),
                "classification": res.get("classification"),
                "route_result": res.get("route_result")
            }
        elif res.get("current_stage") == "ESCALATED":
            return {
                "status": "needs_review",
                "document_id": res.get("document_id"),
                "classification": res.get("classification"),
                "route_result": res.get("route_result")
            }
        else:
            raise HTTPException(status_code=500, detail=res.get("error", "Workflow execution failed"))
            
    except Exception as exc:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/history")
def get_history():
    try:
        conn = get_connection(config)
        cur = conn.execute("""
            SELECT id, entry_id, document_id, filename, timestamp, stage, classification, confidence, routing_destination, error, processing_time_ms
            FROM audit_logs
            ORDER BY id DESC
            LIMIT 100
        """)
        rows = cur.fetchall()
        logs = []
        for r in rows:
            logs.append({
                "id": r[0],
                "entry_id": r[1],
                "document_id": r[2],
                "filename": r[3],
                "timestamp": r[4],
                "stage": r[5],
                "classification": r[6],
                "confidence": r[7],
                "routing_destination": r[8],
                "error": r[9],
                "processing_time_ms": r[10]
            })
        return logs
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
