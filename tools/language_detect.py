import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def detect_language(text: str) -> Dict[str, object]:
    if not text or not text.strip():
        return {"language": "unknown", "confidence": 0.0}

    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        results = detect_langs(text)
        if not results:
            return {"language": "unknown", "confidence": 0.0}

        best = results[0]
        language = best.lang
        confidence = float(best.prob)
        if confidence < 0.7:
            return {"language": "unknown", "confidence": 0.0}
        return {"language": language, "confidence": confidence}
    except Exception as exc:
        logger.warning("Language detection failed: %s", exc)
        return {"language": "unknown", "confidence": 0.0}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Detect language of a text string")
    parser.add_argument("--text", required=True, help="Text to analyze")
    args = parser.parse_args()
    print(json.dumps(detect_language(args.text)))
