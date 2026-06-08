import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF is not installed. PDF extraction is unavailable.")
        return ""

    if not os.path.exists(pdf_path):
        logger.warning("PDF path does not exist: %s", pdf_path)
        return ""

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        logger.warning("Unable to open PDF: %s", exc)
        return ""

    text_chunks = []
    for page in doc:
        try:
            page_text = page.get_text().strip()
            if page_text:
                text_chunks.append(page_text)
        except Exception as exc:
            logger.warning("Error extracting text from page: %s", exc)

    result = "\n\n".join(text_chunks).strip()
    if len(result) < 50:
        ocr_text = _perform_ocr_fallback(doc)
        if ocr_text and len(ocr_text) > len(result):
            result = ocr_text
    return result


def _perform_ocr_fallback(doc) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.debug("OCR fallback not available; pytesseract or Pillow not installed.")
        return ""

    text_chunks = []
    for page in doc:
        try:
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img).strip()
            if page_text:
                text_chunks.append(page_text)
        except Exception as exc:
            logger.warning("OCR fallback failed on page: %s", exc)
    return "\n\n".join(text_chunks).strip()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract text from a PDF file")
    parser.add_argument("--file", required=True, help="Path to the PDF file")
    args = parser.parse_args()
    text = extract_text_from_pdf(args.file)
    print(text)
