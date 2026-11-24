"""Phase 5: Spec-compliant stigmergy memory models (memory.md §2).

Exact schema from spec + helpers. Backed by Redis when available,
local mirror otherwise.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys
from typing import Dict, List, Optional, Set
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pydantic import BaseModel, ConfigDict, Field


class PheromoneTrace(BaseModel):
    node_id: str
    intensity: float = Field(default=1.0, description="Pheromone score [0.0 - 1.0]")
    visited_by: str = Field(description="Agent worker identifier")
    timestamp: float = Field(default_factory=time.time)


class VisitedEdge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float


class BlackboardState(BaseModel):
    query_id: str
    original_prompt: str = ""
    sub_intents: List[str] = []
    seed_node_ids: List[str] = []

    # Stigmergy memory
    node_pheromones: Dict[str, PheromoneTrace] = {}
    explored_edges: List[VisitedEdge] = []
    blacklisted_nodes: Set[str] = set()

    # Evidence Assembly
    evidence_chains: List[List[str]] = Field(default=[], description="Ordered node sequences answering query")
    traversal_complete: bool = False
    status_message: str = "Initializing swarm..."

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ---- spec §3.1 deposit ----
    def deposit(self, node_id: str, agent: str, intensity: float = 1.0):
        self.node_pheromones[node_id] = PheromoneTrace(
            node_id=node_id, intensity=min(1.0, intensity),
            visited_by=agent, timestamp=time.time())

    # ---- spec §3.1 dead-end blacklist ----
    def blacklist_dead_end(self, node_id: str, agent: str = "?"):
        self.node_pheromones[node_id] = PheromoneTrace(
            node_id=node_id, intensity=0.0, visited_by=agent, timestamp=time.time())
        self.blacklisted_nodes.add(node_id)

    # ---- spec §3.2 evaporation: τ(t) = τ(t-1) × (1 − ρ), ρ = 0.15 ----
    def evaporate(self, rho: float = 0.15):
        for nid, trace in list(self.node_pheromones.items()):
            trace.intensity = round(trace.intensity * (1 - rho), 6)
            if trace.intensity < 1e-6 and nid in self.blacklisted_nodes:
                pass  # blacklisted stays blacklisted at 0.0

    def record_edge(self, source: str, target: str, relation: str, confidence: float):
        self.explored_edges.append(VisitedEdge(
            source=source, target=target, relation=relation, confidence=confidence))

    def add_evidence_chain(self, chain: List[str]):
        if chain and chain not in self.evidence_chains:
            self.evidence_chains.append(chain)

    def to_redis_hash(self) -> Dict[str, str]:
        return {
            "state": self.model_dump_json(),
            "updated_at": str(time.time()),
        }

    @classmethod
    def from_redis_hash(cls, data: Dict) -> "BlackboardState":
        raw = data.get("state") or data.get(b"state")
        if isinstance(raw, bytes):
            raw = raw.decode()
        if isinstance(raw, str):
            return cls.model_validate_json(raw)
        return cls(query_id=str(data.get("query_id", "unknown")))
