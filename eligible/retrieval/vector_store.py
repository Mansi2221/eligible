"""Trial retrieval over Pinecone with integrated embeddings + reranking.

Candidate generation for matching: given a patient phenotype, retrieve the
trials most likely to be relevant, so the (expensive) per-criterion LLM matching
only runs on plausible pairs instead of every patient x every trial.

Uses Pinecone integrated inference, text is embedded server-side on upsert and
query (model: multilingual-e5-large), and a cross-encoder reranker
(bge-reranker-v2-m3) reorders the initial hits for precision.
"""

from __future__ import annotations

import time

from pinecone import Pinecone

from eligible.config import get_settings

EMBED_MODEL = "multilingual-e5-large"
RERANK_MODEL = "bge-reranker-v2-m3"
NAMESPACE = "trials"
TEXT_FIELD = "chunk_text"


class TrialRetriever:
    def __init__(self, index_name: str | None = None) -> None:
        settings = get_settings()
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = index_name or settings.pinecone_index
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self) -> None:
        if self.pc.has_index(self.index_name):
            return
        self.pc.create_index_for_model(
            name=self.index_name,
            cloud="aws",
            region="us-east-1",
            embed={"model": EMBED_MODEL, "field_map": {"text": TEXT_FIELD}},
        )
        while not self.pc.describe_index(self.index_name).status.get("ready"):
            time.sleep(1)

    def index_trials(self, trials: list[dict]) -> int:
        """Upsert trial records. Each dict needs nct_id + chunk_text (+ metadata)."""
        records = [
            {"_id": t["nct_id"], TEXT_FIELD: t["chunk_text"], **t.get("metadata", {})}
            for t in trials
        ]
        # upsert in batches of 90 (integrated-inference cap)
        for i in range(0, len(records), 90):
            self.index.upsert_records(namespace=NAMESPACE, records=records[i : i + 90])
        return len(records)

    def search(self, patient_text: str, top_k: int = 15, rerank_n: int = 5) -> list[dict]:
        """Return the top reranked trials for a patient phenotype."""
        res = self.index.search(
            namespace=NAMESPACE,
            query={"inputs": {"text": patient_text}, "top_k": top_k},
            rerank={"model": RERANK_MODEL, "top_n": rerank_n, "rank_fields": [TEXT_FIELD]},
        )
        hits = res.get("result", {}).get("hits", [])
        return [
            {
                "nct_id": h.id,
                "score": h.score,
                "text": h.fields.get(TEXT_FIELD, ""),
            }
            for h in hits
        ]
