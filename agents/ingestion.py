import time
import uuid
from datetime import datetime

from tools.language_detect import detect_language
from tools.pdf_reader import extract_text_from_pdf
from agents.classifier import ClassifierAgent


class IngestionAgent:
    def __init__(self, config: dict):
        self.config = config
        self.classifier = ClassifierAgent(config)

    def run(self, input_data: dict) -> dict:
        pdf_path = input_data.get("pdf_path", "")
        document_id = str(uuid.uuid4())
        start_ts = datetime.utcnow()
        text = extract_text_from_pdf(pdf_path)
        extraction_status = self._determine_extraction_status(text)
        language = detect_language(text)
        classification = self.classifier.run({
            "text": text,
            "language": language,
            "filename": input_data.get("filename") or pdf_path,
        })
        end_ts = datetime.utcnow()
        return {
            "document_id": document_id,
            "filename": input_data.get("filename") or pdf_path,
            "pdf_path": pdf_path,
            "text": text,
            "text_length": len(text or ""),
            "extraction_status": extraction_status,
            "language": language,
            "classification": classification,
            "status": "success" if extraction_status == "success" else "partial",
            "processing_start": start_ts.isoformat() + "Z",
            "processing_end": end_ts.isoformat() + "Z",
            "processing_time_ms": int((end_ts - start_ts).total_seconds() * 1000),
            "errors": [],
        }

    def _determine_extraction_status(self, text: str) -> str:
        if not text or len(text.strip()) < 10:
            return "failed"
        if len(text.strip()) < 100:
            return "partial"
        return "success"
