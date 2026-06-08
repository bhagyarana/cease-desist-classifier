from typing import Dict


class JudgeAgent:
    def __init__(self, config: dict):
        self.config = config

    def run(self, classifier_output: dict, original_text: str) -> Dict[str, object]:
        confidence = classifier_output.get("confidence", 0.0)
        label = classifier_output.get("label", "UNCERTAIN")
        if label == "UNCERTAIN" or confidence < 0.75:
            return {
                "judge_agrees": False,
                "judge_confidence": 0.68,
                "citation_valid": True,
                "issues_found": ["Low confidence or uncertain classification"],
                "correction": None,
            }
        return {
            "judge_agrees": True,
            "judge_confidence": min(1.0, confidence - 0.05),
            "citation_valid": True,
            "issues_found": [],
            "correction": None,
        }
