import os
import sys
import json
import logging
from typing import Dict, Any

from tools.db import get_connection, initialize_sqlite
from tools.rag_service import RAGService
from agents.workflow import CeaseGuardWorkflow
from main import load_config

# Configure simple stderr logging so we don't pollute stdout (which is used for JSON-RPC)
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ceaseguard-mcp-server")


def load_workflow() -> CeaseGuardWorkflow:
    config = load_config()
    if config.get("datastore", {}).get("type") == "sqlite":
        initialize_sqlite(config["datastore"]["sqlite_path"])
    return CeaseGuardWorkflow(config)


def classify_document_tool(pdf_path: str) -> Dict[str, Any]:
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}"}
    try:
        workflow = load_workflow()
        state = {
            "pdf_path": pdf_path,
            "filename": os.path.basename(pdf_path)
        }
        res = workflow.run(state)
        return {
            "document_id": res.get("document_id"),
            "filename": res.get("filename"),
            "stage": res.get("current_stage"),
            "classification": res.get("classification"),
            "language": res.get("language"),
            "route_result": res.get("route_result"),
            "processing_time_ms": res.get("processing_time_ms")
        }
    except Exception as exc:
        return {"error": str(exc)}


def search_cease_requests_tool(query: str, limit: int = 5) -> Dict[str, Any]:
    config = load_config()
    conn = get_connection(config)
    results = []
    try:
        with conn:
            cursor = conn.execute(
                """
                SELECT id, filename, date_received, processed_at, classification_label, confidence, citation, reasoning, language, human_override 
                FROM cease_requests 
                WHERE filename LIKE ? OR reasoning LIKE ? OR citation LIKE ? 
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit)
            )
            rows = cursor.fetchall()
            for row in rows:
                results.append(dict(row))
        return {"results": results}
    except Exception as exc:
        return {"error": str(exc)}


def get_similar_cases_tool(query_text: str, limit: int = 3) -> Dict[str, Any]:
    try:
        config = load_config()
        rag = RAGService(config)
        matches = rag.find_similar(query_text, limit=limit)
        return {"matches": matches}
    except Exception as exc:
        return {"error": str(exc)}


def get_recent_audit_tool(limit: int = 5) -> Dict[str, Any]:
    config = load_config()
    postgres_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or config.get("datastore", {}).get("postgres_url")
    db_type = config.get("datastore", {}).get("type", "sqlite")

    results = []
    try:
        if db_type == "postgres" or postgres_url:
            conn = get_connection(config)
            with conn:
                cursor = conn.execute(
                    """
                    SELECT entry_id, document_id, filename, timestamp, stage, classification, confidence, routing_destination, error
                    FROM audit_logs 
                    ORDER BY created_at DESC 
                    LIMIT ?
                    """,
                    (limit,)
                )
                rows = cursor.fetchall()
                for row in rows:
                    results.append(dict(row))
        else:
            # Fallback to reading JSONL
            audit_path = config.get("files", {}).get("audit_path", "data/audit.jsonl")
            if os.path.exists(audit_path):
                with open(audit_path, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
                    for line in reversed(lines):
                        if len(results) >= limit:
                            break
                        if line.strip():
                            results.append(json.loads(line))
        return {"audit_logs": results}
    except Exception as exc:
        return {"error": str(exc)}


# MCP Protocol Implementation (JSON-RPC 2.0 over stdin/stdout)
TOOLS = [
    {
        "name": "classify_document",
        "description": "Ingest and classify a Cease & Desist PDF document using the stateful multi-agent pipeline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pdf_path": {"type": "string", "description": "Absolute filesystem path to the PDF document."}
            },
            "required": ["pdf_path"]
        }
    },
    {
        "name": "search_cease_requests",
        "description": "Search for indexed compliance records (C&D requests) in the database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword matching filename, reasoning, or citation text."},
                "limit": {"type": "integer", "description": "Maximum number of records to return, default 5."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_similar_cases",
        "description": "Perform a semantic RAG similarity search against previous C&D document summaries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_text": {"type": "string", "description": "Paragraph or text summary to find similar cases for."},
                "limit": {"type": "integer", "description": "Maximum number of matches to retrieve, default 3."}
            },
            "required": ["query_text"]
        }
    },
    {
        "name": "get_recent_audit",
        "description": "Retrieve recent audit trail logs from the database or flat JSONL audit file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of logs to return, default 5."}
            }
        }
    }
]


def send_response(req_id: Any, result: Any = None, error: Any = None):
    response: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": req_id
    }
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle_request(request: Dict[str, Any]):
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if not method:
        return

    logger.info(f"Received MCP request: id={req_id}, method={method}")

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "ceaseguard-mcp-server",
                "version": "1.0.0"
            }
        }
        send_response(req_id, result=result)
        
    elif method == "tools/list":
        result = {"tools": TOOLS}
        send_response(req_id, result=result)
        
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Calling tool: {tool_name} with args {arguments}")
        
        tool_result = None
        if tool_name == "classify_document":
            tool_result = classify_document_tool(arguments.get("pdf_path", ""))
        elif tool_name == "search_cease_requests":
            tool_result = search_cease_requests_tool(
                arguments.get("query", ""),
                limit=arguments.get("limit", 5)
            )
        elif tool_name == "get_similar_cases":
            tool_result = get_similar_cases_tool(
                arguments.get("query_text", ""),
                limit=arguments.get("limit", 3)
            )
        elif tool_name == "get_recent_audit":
            tool_result = get_recent_audit_tool(limit=arguments.get("limit", 5))
        else:
            send_response(req_id, error={"code": -32601, "message": f"Method not found: {tool_name}"})
            return

        # Return standard MCP tool execution format
        mcp_content = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(tool_result, ensure_ascii=False, indent=2)
                }
            ],
            "isError": "error" in tool_result
        }
        send_response(req_id, result=mcp_content)
    else:
        send_response(req_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main():
    logger.info("Starting CeaseGuard MCP server...")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            handle_request(request)
        except Exception as exc:
            logger.error(f"Error reading JSON request: {exc}")
            send_response(None, error={"code": -32700, "message": "Parse error"})


if __name__ == "__main__":
    main()
