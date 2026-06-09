import pytest

from agents.classifier import ClassifierAgent


def test_classifier_cease_detects_cease_language():
    config = {"classifier": {"model": "mock", "confidence_threshold_uncertain": 0.75, "confidence_threshold_edge_case": 0.60}}
    agent = ClassifierAgent(config)
    result = agent.run({
        "text": "I hereby request you cease all communications immediately.",
        "language": {"language": "en"},
        "filename": "cease.pdf",
    })

    assert result["label"] == "CEASE"
    assert result["confidence"] >= 0.8
    assert "cease" in result["citation"].lower()


def test_classifier_irrelevant_detects_billing_language():
    config = {"classifier": {"model": "mock", "confidence_threshold_uncertain": 0.75, "confidence_threshold_edge_case": 0.60}}
    agent = ClassifierAgent(config)
    result = agent.run({
        "text": "Please find the attached invoice for your account.",
        "language": {"language": "en"},
        "filename": "invoice.pdf",
    })

    assert result["label"] == "IRRELEVANT"
    assert result["confidence"] >= 0.8


def test_classifier_uncertain_for_ambiguous_text():
    config = {"classifier": {"model": "mock", "confidence_threshold_uncertain": 0.75, "confidence_threshold_edge_case": 0.60}}
    agent = ClassifierAgent(config)
    result = agent.run({
        "text": "Please review this request and advise what to do next.",
        "language": {"language": "en"},
        "filename": "ambiguous.pdf",
    })

    assert result["label"] == "UNCERTAIN"
    assert result["confidence"] < 0.75


def test_classifier_translates_spanish_cease_citation():
    config = {"classifier": {"model": "mock", "confidence_threshold_uncertain": 0.75, "confidence_threshold_edge_case": 0.60}}
    agent = ClassifierAgent(config)
    result = agent.run({
        "text": "Dejen de enviarnos correos de marketing inmediatamente.",
        "language": {"language": "es"},
        "filename": "spanish_cease.pdf",
    })

    assert result["label"] == "CEASE"
    assert result["confidence"] >= 0.8
    assert "stop sending us marketing emails" in result["citation"].lower()
