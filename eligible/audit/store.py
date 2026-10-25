"""File-backed persistent audit log.

Wraps the in-memory `AuditChain` with append-only JSONL persistence so the
tamper-evident chain survives restarts. On load it rebuilds the chain and can
re-verify the full history, the check an auditor runs.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from eligible.audit.chain import AuditChain, AuditEntry


class FileAuditLog:
    def __init__(self, path: str = "data/audit_log.jsonl") -> None:
        self.path = path
        self.chain = AuditChain()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.chain._entries.append(AuditEntry(**json.loads(line)))

    def append(self, event_type: str, payload: dict) -> AuditEntry:
        entry = self.chain.append(event_type, payload)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def verify(self) -> int | None:
        """Return the index of the first broken entry, or None if intact."""
        return self.chain.verify_chain()

    def entries(self) -> list[dict]:
        return self.chain.to_list()

    def __len__(self) -> int:
        return len(self.chain._entries)
