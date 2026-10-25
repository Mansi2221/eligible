"""Load n2c2 2018 Track 1 XML records.

Each file is one patient: free-text record in <TEXT>, gold labels in <TAGS>
(e.g. `<ABDOMINAL met="not met" />`). Returns records with text + gold dict.
"""

from __future__ import annotations

import glob
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from eligible.eval.n2c2.criteria import CRITERIA_CODES, MET, NOT_MET


@dataclass
class N2C2Record:
    patient_id: str
    text: str
    gold: dict[str, str]  # criterion code -> "met" | "not met"


def _normalize(value: str | None) -> str:
    return MET if (value or "").strip().lower() == MET else NOT_MET


def load_record(path: str) -> N2C2Record:
    root = ET.parse(path).getroot()
    text = (root.findtext("TEXT") or "").strip()
    tags = root.find("TAGS")
    gold: dict[str, str] = {}
    if tags is not None:
        for code in CRITERIA_CODES:
            el = tags.find(code)
            gold[code] = _normalize(el.get("met") if el is not None else None)
    pid = os.path.splitext(os.path.basename(path))[0]
    return N2C2Record(patient_id=pid, text=text, gold=gold)


def load_records(directory: str) -> list[N2C2Record]:
    files = sorted(glob.glob(os.path.join(directory, "*.xml")))
    return [load_record(f) for f in files]
