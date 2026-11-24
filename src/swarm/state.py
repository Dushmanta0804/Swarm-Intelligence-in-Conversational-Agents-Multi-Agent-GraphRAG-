"""Pydantic schemas for swarm state (architecture: backend/app/models/agent_state.py)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubGoal(BaseModel):
    id: str
    question: str
    seed_entities: List[str] = Field(default_factory=list)
    expected_hops: int = 2


class SeedNode(BaseModel):
    node_id: str
    name: str
    anchor_score: float
    source: str = "scout"  # vector | lexical | vector+lexical
    chunk_id: Optional[str] = None


class TracedPath(BaseModel):
    nodes: List[str]
    node_names: List[str] = Field(default_factory=list)
    edges: List[str] = Field(default_factory=list)
    score: float
    hops: int
    evidence_chunks: List[str] = Field(default_factory=list)
    pruned: bool = False
    prune_reason: Optional[str] = None


class SwarmState(BaseModel):
    query: str
    query_id: str
    sub_goals: List[SubGoal] = Field(default_factory=list)
    seeds: List[SeedNode] = Field(default_factory=list)
    candidate_paths: List[TracedPath] = Field(default_factory=list)
    validated_paths: List[TracedPath] = Field(default_factory=list)
    llm_calls: int = 0  # Phase 2 deterministic: stays 0 (proves token efficiency)
    pruned_count: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
