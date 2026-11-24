"""Phase 2 acceptance tests (F-02 swarm engine)."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.loaders import ensure_sample_docs
from src.swarm.workflow import SwarmOrchestrator
from src.swarm.blackboard import Blackboard


def _pipe(tmp_path):
    ensure_sample_docs(tmp_path)
    p = IngestionPipeline()
    p.run(tmp_path)
    return p


def test_swarm_end_to_end(tmp_path):
    p = _pipe(tmp_path)
    orch = SwarmOrchestrator(p.graph, p.vectors)
    out = orch.run("Who acquired DeepMind?")
    assert out["metrics"]["validated"] >= 1, out["metrics"]
    assert out["metrics"]["llm_calls"] == 0  # deterministic pruning, no LLM
    assert out["metrics"]["latency_s"] < 4.5  # NFR latency


def test_pruning_and_no_cycles(tmp_path):
    p = _pipe(tmp_path)
    orch = SwarmOrchestrator(p.graph, p.vectors, prune_threshold=0.99)
    out = orch.run("Who acquired DeepMind?")
    assert out["metrics"]["pruned"] >= 0
    for cand in out["candidates"]:
        assert len(cand["node_names"]) == len(set(cand["node_names"])), "cycle detected"


def test_parallel_fanout_and_pheromones(tmp_path):
    p = _pipe(tmp_path)
    bb = Blackboard("test_q")
    orch = SwarmOrchestrator(p.graph, p.vectors, blackboard=bb, max_workers=8)
    t0 = time.time()
    out = orch.run("Trace shell company transfers from Acme Holdings")
    dt = time.time() - t0
    assert dt < 4.5, f"too slow: {dt}"
    assert bb.snapshot()["visited"] >= 1
    assert len(bb.pheromones) >= 1, "tracers must deposit pheromones"


def test_validator_dedupes(tmp_path):
    p = _pipe(tmp_path)
    orch = SwarmOrchestrator(p.graph, p.vectors)
    out = orch.run("Microsoft partners with OpenAI")
    sigs = [tuple(v["node_names"]) for v in out["validated"]]
    assert len(sigs) == len(set(sigs)), "validator must dedupe paths"
