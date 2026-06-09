import logging
import os
import re
from typing import Dict, Optional

from agents.prompts import ACTIVE_CLASSIFIER_PROMPT, ACTIVE_TRANSLATION_PROMPT

logger = logging.getLogger(__name__)

CEASE_KEYWORDS = [
    "cease all communication",
    "do not contact",
    "do not call",
    "do not email",
    "unsubscribe from all",
    "stop all communications",
    "stop all communication",
    "stop sending us marketing emails",
    "stop sending me marketing emails",
    "stop sending marketing emails",
    "cease and desist",
    "cease all",
    "stop contacting me",
    "stop contacting us",
    "remove me from your list",
]
IRRELEVANT_KEYWORDS = [
    "invoice",
    "billing",
    "payment",
    "statement",
    "order",
    "service request",
    "complaint",
    "account dispute",
    "contract",
    "legal dispute",
]

SPANISH_TRANSLATION_MAP = [
    ("dejen de enviarnos correos de marketing", "stop sending us marketing emails"),
    ("dejar de enviarnos correos de marketing", "stop sending us marketing emails"),
    ("dejen de contactarnos", "stop contacting us"),
    ("no me contacten", "do not contact me"),
    ("no nos contacten", "do not contact us"),
    ("factura", "invoice"),
    ("pago", "payment"),
    ("consulta", "inquiry"),
    ("solicitud", "request"),
]

FRENCH_TRANSLATION_MAP = [
    ("cessez de nous envoyer des e-mails marketing", "stop sending us marketing emails"),
    ("ne me contactez pas", "do not contact me"),
    ("ne nous contactez pas", "do not contact us"),
    ("facture", "invoice"),
    ("paiement", "payment"),
    ("demande", "request"),
]


class ClassifierAgent:
    def __init__(self, config: dict):
        self.config = config
        self._api_key = os.environ.get("ANTHROPIC_API_KEY")
        self._model = config.get("classifier", {}).get("model", "claude-sonnet-4-20250514")
        self._confidence_threshold_uncertain = config.get("classifier", {}).get("confidence_threshold_uncertain", 0.75)
        self._confidence_threshold_edge_case = config.get("classifier", {}).get("confidence_threshold_edge_case", 0.60)

    def run(self, payload: dict) -> Dict[str, object]:
        text = payload.get("text", "") or ""
        language = payload.get("language", {}).get("language", "unknown")
        filename = payload.get("filename", "unknown")
        if not text.strip():
            return {
                "label": "UNCERTAIN",
                "confidence": 0.0,
                "citation": "",
                "reasoning": "No text could be extracted from the document.",
                "edge_case_flag": True,
                "model": self._model,
                "prompt_version": "v1.0.0",
                "error": "empty_text",
            }

        if self._api_key and self._can_call_anthropic():
            try:
                return self._call_anthropic(text, language, filename)
            except Exception as exc:
                logger.warning("Anthropic classification failed: %s", exc)

        return self._heuristic_classify(text, language)

    def _can_call_anthropic(self) -> bool:
        try:
            import anthropic  # type: ignore
            return True
        except ImportError:
            return False

    def _call_anthropic(self, text: str, language: str, filename: str) -> Dict[str, object]:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        prompt = f"{ACTIVE_CLASSIFIER_PROMPT}\n\nDocument text:\n{text[:20000]}"
        response = client.completions.create(
            model=self._model,
            prompt=prompt,
            max_tokens_to_sample=512,
            temperature=0.0,
        )
        raw_output = response.get("completion", "")
        parsed = self._parse_json(raw_output)
        if parsed and self._validate_citation(parsed.get("citation", ""), text):
            return self._finalize_output(self._apply_thresholds(parsed), text, language)
        return self._heuristic_classify(text, language)

    def _parse_json(self, raw_text: str) -> Optional[Dict[str, object]]:
        try:
            import json
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start == -1 or end == -1:
                return None
            return json.loads(raw_text[start:end + 1])
        except Exception:
            return None

    def _validate_citation(self, citation: str, text: str) -> bool:
        return bool(citation and citation in text)

    def _apply_thresholds(self, parsed: dict) -> dict:
        label = parsed.get("label", "UNCERTAIN")
        confidence = float(parsed.get("confidence", 0.0))
        edge_case = bool(parsed.get("edge_case_flag", False))
        if confidence < self._confidence_threshold_edge_case:
            return {
                "label": "UNCERTAIN",
                "confidence": 0.0,
                "citation": parsed.get("citation", ""),
                "reasoning": parsed.get("reasoning", "Low confidence forced UNCERTAIN."),
                "edge_case_flag": True,
                "model": self._model,
                "prompt_version": "v1.0.0",
            }
        if confidence < self._confidence_threshold_uncertain:
            return {
                "label": "UNCERTAIN",
                "confidence": confidence,
                "citation": parsed.get("citation", ""),
                "reasoning": parsed.get("reasoning", "Confidence below threshold forced UNCERTAIN."),
                "edge_case_flag": edge_case or True,
                "model": self._model,
                "prompt_version": "v1.0.0",
            }
        return {
            "label": label,
            "confidence": confidence,
            "citation": parsed.get("citation", ""),
            "reasoning": parsed.get("reasoning", ""),
            "edge_case_flag": edge_case,
            "model": self._model,
            "prompt_version": "v1.0.0",
        }

    def _heuristic_classify(self, text: str, language: str) -> Dict[str, object]:
        translated_text = self._translate_text_for_language(text, language)
        lower = translated_text.lower()
        cease_score = sum(1 for token in CEASE_KEYWORDS if token in lower)
        irrelevant_score = sum(1 for token in IRRELEVANT_KEYWORDS if token in lower)
        citation = self._find_citation(lower, CEASE_KEYWORDS if cease_score >= irrelevant_score else IRRELEVANT_KEYWORDS, translated_text)
        if cease_score > 0 and cease_score >= irrelevant_score:
            confidence = 0.9
            label = "CEASE"
            reasoning = "The document contains explicit cease request language."
        elif irrelevant_score > 0 and irrelevant_score > cease_score:
            confidence = 0.85
            label = "IRRELEVANT"
            reasoning = "The document contains billing or general inquiry language unrelated to cease requests."
        elif cease_score > 0 and irrelevant_score > 0:
            confidence = 0.65
            label = "UNCERTAIN"
            reasoning = "The document contains mixed signals between cease language and non-cease content."
        else:
            confidence = 0.5
            label = "UNCERTAIN"
            reasoning = "Unable to determine whether the document is a cease request."

        if confidence < self._confidence_threshold_edge_case:
            edge_case = True
        elif confidence < self._confidence_threshold_uncertain:
            edge_case = True
        else:
            edge_case = False

        return {
            "label": label,
            "confidence": confidence,
            "citation": citation,
            "reasoning": reasoning + (" Document language: %s." % language if language != "en" else ""),
            "edge_case_flag": edge_case,
            "model": self._model,
            "prompt_version": "v1.0.0",
        }

    def _finalize_output(self, result: Dict[str, object], original_text: str, language: str) -> Dict[str, object]:
        if language != "en":
            result = dict(result)
            result["citation"] = self._translate_citation_to_english(str(result.get("citation", "")), language)
            reasoning = str(result.get("reasoning", "")).strip()
            language_note = f" Document language: {language}."
            if language_note.strip() not in reasoning:
                result["reasoning"] = (reasoning + language_note).strip()
            result["edge_case_flag"] = bool(result.get("edge_case_flag", False)) or not result.get("citation")
        return result

    def _translate_text_for_language(self, text: str, language: str) -> str:
        if language == "es":
            return self._apply_phrase_map(text, SPANISH_TRANSLATION_MAP)
        if language == "fr":
            return self._apply_phrase_map(text, FRENCH_TRANSLATION_MAP)
        return text

    def _translate_citation_to_english(self, citation: str, language: str) -> str:
        if not citation:
            return citation

        if self._api_key and self._can_call_anthropic():
            try:
                return self._call_translation_model(citation, language)
            except Exception as exc:
                logger.warning("Translation via Anthropic failed: %s", exc)

        return self._translate_text_for_language(citation, language)

    def _call_translation_model(self, citation: str, language: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        prompt = ACTIVE_TRANSLATION_PROMPT.format(source_language=language, citation_text=citation[:4000])
        response = client.completions.create(
            model=self._model,
            prompt=prompt,
            max_tokens_to_sample=128,
            temperature=0.0,
        )
        translated = (response.get("completion", "") or "").strip()
        return translated or citation

    def _apply_phrase_map(self, text: str, phrase_map: list[tuple[str, str]]) -> str:
        updated = text
        lowered = text.lower()
        for source_phrase, translated_phrase in phrase_map:
            if source_phrase in lowered:
                updated = re.sub(re.escape(source_phrase), translated_phrase, updated, flags=re.IGNORECASE)
                lowered = updated.lower()
        return updated

    def _find_citation(self, lowered_text: str, keywords: list, original_text: str) -> str:
        for keyword in keywords:
            idx = lowered_text.find(keyword)
            if idx != -1:
                origin_idx = original_text.lower().find(keyword)
                if origin_idx != -1:
                    return original_text[origin_idx: origin_idx + min(200, len(keyword) + 100)].strip()
        return original_text[:200].strip()
