"""Tests for the regex layer of PHI redaction (NER layer is optional)."""

from eligible.redaction import Redactor


def _r():
    # Force regex-only so tests don't depend on a spaCy model being installed.
    return Redactor(use_ner=False)


def test_redacts_ssn_phone_email():
    text = "Contact 555-12-3456, call (617) 555-0192 or email jane@clinic.org."
    res = _r().redact(text)
    assert "555-12-3456" not in res.text
    assert "jane@clinic.org" not in res.text
    labels = {d.label for d in res.detections}
    assert {"SSN", "PHONE", "EMAIL"} <= labels


def test_redacts_mrn_and_date():
    text = "Patient MRN 0042199 admitted on 03/14/2021."
    res = _r().redact(text)
    assert "0042199" not in res.text
    assert "03/14/2021" not in res.text
    assert any(d.label == "MRN" for d in res.detections)
    assert any(d.label == "DATE" for d in res.detections)


def test_surrogate_tokens_are_deterministic_per_value():
    text = "Call 617-555-0192, or 617-555-0192 again."  # same number twice
    res = _r().redact(text)
    # Same value -> same surrogate token both times.
    assert res.text.count("[PHONE_1]") == 2
    assert "[PHONE_2]" not in res.text


def test_clean_text_is_unchanged():
    text = "Patient has type 2 diabetes and elevated HbA1c."
    res = _r().redact(text)
    assert res.text == text
    assert res.count == 0
