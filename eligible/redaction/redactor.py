"""Hybrid PHI redaction middleware.

Two layers, matching the HIPAA Safe Harbor identifier list:

1. **Regex**, microsecond, high-precision structured identifiers (SSN, phone,
   email, MRN, dates, ZIP, URL, IP).
2. **NER (optional)**, contextual identifiers (person names, locations) via
   spaCy if a model is installed. Degrades gracefully to regex-only when not.

Detected PHI is replaced with deterministic surrogate tokens
(``[PATIENT_NAME_1]``, ``[SSN_1]``) *before* any payload leaves the local
network for an external API. This runs on patient notes, never on the public
trial criteria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Order matters: more specific patterns first so they win overlapping matches.
PATTERNS: dict[str, re.Pattern] = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "MRN": re.compile(r"\bMRN[:#]?\s?\d{4,10}\b", re.IGNORECASE),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "URL": re.compile(r"\bhttps?://\S+\b"),
    "IP": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "DATE": re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
    ),
    "ZIP": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
}


@dataclass
class Detection:
    label: str
    start: int
    end: int
    text: str


@dataclass
class RedactionResult:
    text: str
    detections: list[Detection] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.detections)


class Redactor:
    def __init__(self, use_ner: bool = True) -> None:
        self._nlp = _load_spacy() if use_ner else None

    def redact(self, text: str) -> RedactionResult:
        detections: list[Detection] = []

        # --- layer 1: regex ---
        for label, pattern in PATTERNS.items():
            for m in pattern.finditer(text):
                detections.append(Detection(label, m.start(), m.end(), m.group()))

        # --- layer 2: NER (names, locations) ---
        if self._nlp is not None:
            doc = self._nlp(text)
            for ent in doc.ents:
                if ent.label_ in {"PERSON", "GPE", "LOC", "FAC"}:
                    label = "PATIENT_NAME" if ent.label_ == "PERSON" else "LOCATION"
                    detections.append(Detection(label, ent.start_char, ent.end_char, ent.text))

        detections = _resolve_overlaps(detections)
        redacted = _apply(text, detections)
        return RedactionResult(text=redacted, detections=detections)


def _resolve_overlaps(dets: list[Detection]) -> list[Detection]:
    """Keep the earliest, longest match when spans overlap."""
    dets = sorted(dets, key=lambda d: (d.start, -(d.end - d.start)))
    kept: list[Detection] = []
    last_end = -1
    for d in dets:
        if d.start >= last_end:
            kept.append(d)
            last_end = d.end
    return kept


def _apply(text: str, dets: list[Detection]) -> str:
    """Replace spans with deterministic surrogate tokens, numbered per label."""
    counters: dict[str, dict[str, int]] = {}
    out, cursor = [], 0
    for d in sorted(dets, key=lambda d: d.start):
        per_label = counters.setdefault(d.label, {})
        if d.text not in per_label:
            per_label[d.text] = len(per_label) + 1
        token = f"[{d.label}_{per_label[d.text]}]"
        out.append(text[cursor:d.start])
        out.append(token)
        cursor = d.end
    out.append(text[cursor:])
    return "".join(out)


def _load_spacy():  # pragma: no cover - depends on optional model
    try:
        import spacy

        for model in ("en_core_sci_sm", "en_core_web_sm"):
            try:
                return spacy.load(model)
            except OSError:
                continue
    except ImportError:
        pass
    return None
