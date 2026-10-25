"""Tests for the SHA-256 audit chain, the compliance spine."""

from eligible.audit import AuditChain, GENESIS_HASH


def test_empty_chain_head_is_genesis():
    chain = AuditChain()
    assert chain.head_hash == GENESIS_HASH
    assert chain.verify_chain() is None


def test_append_links_to_previous():
    chain = AuditChain()
    first = chain.append("match_decision", {"patient": "P1", "verdict": "eligible"})
    second = chain.append("human_approval", {"reviewer": "R1", "approved": True})

    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.entry_hash
    assert chain.verify_chain() is None


def test_intact_chain_verifies():
    chain = AuditChain()
    for i in range(5):
        chain.append("event", {"n": i})
    assert chain.verify_chain() is None


def test_tampering_breaks_the_chain():
    chain = AuditChain()
    for i in range(5):
        chain.append("event", {"n": i})

    # Silently mutate a historical payload, as a rogue DB admin might.
    tampered_index = 2
    object.__setattr__(chain._entries[tampered_index], "payload", {"n": 999})

    assert chain.verify_chain() == tampered_index


def test_same_payload_hashes_deterministically():
    a, b = AuditChain(), AuditChain()
    ea = a.append("event", {"b": 2, "a": 1})
    eb = b.append("event", {"a": 1, "b": 2})  # key order differs
    assert ea.entry_hash == eb.entry_hash
