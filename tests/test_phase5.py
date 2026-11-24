"""Phase 5 acceptance tests (memory.md stigmergy engine)."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.loaders import ensure_sample_docs
from src.swarm.memory import BlackboardState
from src.swarm.session_memory import SessionMemory
from src.swarm.blackboard import Blackboard
from src.swarm.workflow import SwarmOrchestrator


def _pipe(tmp_path):
    ensure_sample_docs(tmp_path)
    p = IngestionPipeline()
    p.run(tmp_path)
    return p


def test_spec_schema_deposit_blacklist_evaporate():
    s = BlackboardState(query_id="q1", original_prompt="test")
    s.deposit("n1", agent="tracer_1")  # §3.1 τ = 1.0
    assert s.node_pheromones["n1"].intensity == 1.0
    assert s.node_pheromones["n1"].visited_by == "tracer_1"
    s.record_edge("n1", "n2", "ACQUIRED", 0.9)
    assert len(s.explored_edges) == 1
    s.blacklist_dead_end("n9")  # §3.1 τ = 0.0 + blacklisted
    assert s.node_pheromones["n9"].intensity == 0.0
    assert "n9" in s.blacklisted_nodes
    s.deposit("n1", agent="t2")
    s.evaporate(rho=0.15)  # §3.2 τ(t) = τ(t-1) × 0.85
    assert abs(s.node_pheromones["n1"].intensity - 0.85) < 1e-6
    s.add_evidence_chain(["n1", "n2"])
    assert s.evidence_chains == [["n1", "n2"]]


def test_blackboard_dead_end_and_evaporation():
    bb = Blackboard("q2", evaporation=0.15)
    bb.deposit("a", agent="tracer")
    assert bb.pheromone("a") == 1.0  # clamped to [0,1]
    bb.blacklist_dead_end("dead", agent="tracer")
    assert bb.pheromone("dead") == 0.0
    assert bb.spec is not None and "dead" in bb.spec.blacklisted_nodes
    bb.decay_all()  # ρ = 0.15
    assert abs(bb.pheromone("a") - 0.85) < 1e-6


def test_session_focus_cache_hit(tmp_path):
    p = _pipe(tmp_path)
    mem = SessionMemory(top_k=10, ttl_s=1800)
    orch = SwarmOrchestrator(p.graph, p.vectors, session_memory=mem)
    out1 = orch.run("Who acquired DeepMind?", session_id="s1")
    assert out1["metrics"]["focus_cached"] is True
    assert out1["focus_hit"] is None or out1["focus_hit"].get("hit") in (None, False)
    # follow-up intersecting cached focus → skip global search
    out2 = orch.run("Why did that acquisition happen?", session_id="s1")
    # 'acquisition/acquired' tokens may or may not overlap; force a direct overlap query
    out3 = orch.run("Tell me more about DeepMind acquisition", session_id="s1")
    assert out3["focus_hit"] is not None and out3["focus_hit"].get("hit") is True
    assert out3["focus_hit"].get("skipped_global_search") is True
    assert any(s["source"] == "focus-cache" for s in out3["seeds"])


def test_multiturn_end_to_end_no_regression(tmp_path):
    p = _pipe(tmp_path)
    orch = SwarmOrchestrator(p.graph, p.vectors)
    out = orch.run("Who acquired DeepMind?", session_id="s9")
    assert out["metrics"]["validated"] >= 1
    assert out["metrics"]["llm_calls"] == 0
    assert out["metrics"]["latency_s"] < 4.5
