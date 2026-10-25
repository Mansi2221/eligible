"""Tamper-evident audit log via a SHA-256 hash chain.

Every event stores the hash of the previous event, so altering any historical
entry breaks the chain from that point forward. ``verify_chain`` returns the
index of the first broken link (or ``None`` if intact), letting an auditor
prove the log was not silently edited.

This is the compliance spine, the matching agent's reasoning trace, tool
calls, and human approvals all land here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

GENESIS_HASH = "0" * 64


def _hash(prev_hash: str, payload: dict) -> str:
    # Deterministic serialization so the same payload always hashes identically.
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}{body}".encode()).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    index: int
    event_type: str
    payload: dict
    prev_hash: str
    entry_hash: str = field(default="")

    def recompute_hash(self) -> str:
        return _hash(self.prev_hash, self._hashable_payload())

    def _hashable_payload(self) -> dict:
        return {
            "index": self.index,
            "event_type": self.event_type,
            "payload": self.payload,
        }


class AuditChain:
    """An append-only, hash-linked audit log (in-memory reference impl)."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    @property
    def head_hash(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS_HASH

    def append(self, event_type: str, payload: dict) -> AuditEntry:
        index = len(self._entries)
        prev_hash = self.head_hash
        stub = AuditEntry(index=index, event_type=event_type, payload=payload, prev_hash=prev_hash)
        entry = AuditEntry(
            index=index,
            event_type=event_type,
            payload=payload,
            prev_hash=prev_hash,
            entry_hash=stub.recompute_hash(),
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> int | None:
        """Return the index of the first tampered/broken entry, else None."""
        expected_prev = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != expected_prev:
                return entry.index
            if entry.entry_hash != entry.recompute_hash():
                return entry.index
            expected_prev = entry.entry_hash
        return None

    def to_list(self) -> list[dict]:
        return [asdict(e) for e in self._entries]
