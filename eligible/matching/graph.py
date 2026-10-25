"""LangGraph matching pipeline: phenotype -> retrieve -> match.

A stateful graph with three nodes:
  1. phenotype: build the patient profile from OMOP (deterministic)
  2. retrieve: Pinecone candidate trials for that profile
  3. match: per-criterion LLM adjudication of each candidate trial

Dependencies are injected so the graph is testable with fakes.
"""

from __future__ import annotations

import os
from typing import TypedDict

import duckdb
from langgraph.graph import END, START, StateGraph

from eligible.criteria.schema import Criterion
from eligible.matching.matcher import TrialMatcher
from eligible.matching.phenotype import PatientProfile, PhenotypeBuilder
from eligible.matching.schema import TrialMatch

DB_PATH = os.environ.get("ELIGIBLE_DB", "data/eligible.duckdb")


class MatchState(TypedDict, total=False):
    person_id: int
    profile: PatientProfile
    candidates: list[dict]
    matches: list[TrialMatch]


class MatchingPipeline:
    def __init__(self, db_path: str = DB_PATH, retriever=None, matcher=None) -> None:
        self.builder = PhenotypeBuilder(db_path)
        self.matcher = matcher or TrialMatcher()
        self._retriever = retriever  # lazily built (needs Pinecone key) if None
        self.criteria_by_trial = self._load_criteria(db_path)
        self.graph = self._build_graph()

    @property
    def retriever(self):
        if self._retriever is None:
            from eligible.retrieval.vector_store import TrialRetriever

            self._retriever = TrialRetriever()
        return self._retriever

    def _load_criteria(self, db_path: str) -> dict[str, list[Criterion]]:
        con = duckdb.connect(db_path, read_only=True)
        rows = con.execute(
            """SELECT nct_id, kind, text, category, attribute, operator, value, unit, temporal
               FROM raw.trial_criteria"""
        ).fetchall()
        con.close()
        out: dict[str, list[Criterion]] = {}
        for r in rows:
            out.setdefault(r[0], []).append(
                Criterion(
                    kind=r[1], text=r[2], category=r[3], attribute=r[4],
                    operator=r[5], value=r[6], unit=r[7], temporal=r[8],
                )
            )
        return out

    # --- nodes ---
    def _node_phenotype(self, state: MatchState) -> MatchState:
        return {"profile": self.builder.build(state["person_id"])}

    def _node_retrieve(self, state: MatchState) -> MatchState:
        hits = self.retriever.search(state["profile"].to_prompt_text())
        return {"candidates": hits}

    def _node_match(self, state: MatchState) -> MatchState:
        matches = []
        for hit in state["candidates"]:
            nct_id = hit["nct_id"]
            criteria = self.criteria_by_trial.get(nct_id, [])
            if not criteria:
                continue
            matches.append(self.matcher.evaluate(state["profile"], nct_id, criteria))
        return {"matches": matches}

    def _build_graph(self):
        g = StateGraph(MatchState)
        g.add_node("phenotype", self._node_phenotype)
        g.add_node("retrieve", self._node_retrieve)
        g.add_node("match", self._node_match)
        g.add_edge(START, "phenotype")
        g.add_edge("phenotype", "retrieve")
        g.add_edge("retrieve", "match")
        g.add_edge("match", END)
        return g.compile()

    def run(self, person_id: int) -> list[TrialMatch]:
        result = self.graph.invoke({"person_id": person_id})
        return result.get("matches", [])
