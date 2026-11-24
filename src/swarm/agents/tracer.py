"""Path Tracer Swarm — concurrent edge navigation with pheromone deposits + pruning."""
from __future__ import annotations
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from typing import List
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.swarm.state import SeedNode, TracedPath
from src.ingestion.vector_store import embed_text, cosine


def _relevance(query: str, node_name: str, edge_type: str) -> float:
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    s = f"{node_name} {edge_type}".lower()
    t = set(re.findall(r"[a-z0-9]+", s))
    if not q or not t:
        return 0.0
    overlap = len(q & t) / max(1, len(q))
    sem = cosine(embed_text(query), embed_text(f"{node_name} {edge_type}"))
    base = 0.5 * overlap + 0.5 * sem
    # small prior so connected graph structure is explorable even on
    # vocabulary-mismatched queries; pruning still applies below threshold
    return round(min(1.0, base + 0.35), 4)


def trace_from_seed(graph, blackboard, query: str, seed: SeedNode,
                    max_hops: int = 3, prune_threshold: float = 0.60) -> List[TracedPath]:
    paths: List[TracedPath] = []
    seed_name = seed.name
    blackboard.register(f"tracer_{seed.node_id[:8]}", "tracer", seed=seed.node_id)
    # BFS frontier: (node_id, node_names, edges, evidence, score, hops)
    frontier = [(seed.node_id, [seed_name], [], [], 1.0, 0)]
    blackboard.deposit(seed.node_id, agent="tracer")
    # per-path visited set (seed's own chain), NOT the global board:
    # the global board prevents cross-seed duplication via claim below
    local_visited = {seed.node_id}
    while frontier:
        nid, names, edges, evids, score, hops = frontier.pop(0)
        if hops >= max_hops:
            paths.append(TracedPath(nodes=[nid], node_names=names, edges=edges,
                                    score=round(score, 4), hops=hops, evidence_chunks=evids))
            continue
        try:
            nbrs = graph.neighbors(nid)
        except Exception:
            nbrs = []
        extended = False
        for nb in nbrs:
            tgt = nb.get("target") or nb.get("id")
            if not tgt or tgt in local_visited:
                continue  # prevent circular walks within this path
            # spec §3.1: blacklisted dead-ends are never re-entered
            if tgt in getattr(blackboard, "pruned", {}) and blackboard.pruned.get(tgt) == "dead_end":
                continue
            # spec §3.1 negative feedback: high pheromone on non-branching
            # paths deters redundant traversal
            pher = blackboard.pheromone(tgt)
            if pher >= 1.0 and len(nbrs) <= 1:
                blackboard.log("tracer", "pheromone_avoided", node=tgt, level=pher)
                continue
            rel = _relevance(query, nb.get("name", ""), nb.get("type", ""))
            if rel < prune_threshold:
                blackboard.mark_pruned(tgt, f"relevance {rel} < {prune_threshold}", agent="tracer")
                continue  # deterministic prune, no LLM call
            blackboard.mark_visited(tgt, agent="tracer")
            local_visited.add(tgt)
            blackboard.deposit(tgt, amount=rel, agent="tracer")
            try:
                blackboard.record_edge(nid, tgt, nb.get("type", "RELATED"), rel, agent="tracer")
            except Exception:
                pass
            ev = nb.get("evidence_chunk_id") or nb.get("chunk_id")
            frontier.append((tgt, names + [nb.get("name", tgt)],
                             edges + [nb.get("type", "RELATED")],
                             evids + ([ev] if ev else []),
                             score * (0.7 + 0.3 * rel), hops + 1))
            extended = True
        if not extended:
            # spec §3.1: dead end → τ = 0.0 + blacklisted
            try:
                blackboard.blacklist_dead_end(nid, agent="tracer")
            except Exception:
                pass
            paths.append(TracedPath(nodes=[nid], node_names=names, edges=edges,
                                    score=round(score, 4), hops=hops, evidence_chunks=evids))
    blackboard.deregister(f"tracer_{seed.node_id[:8]}")
    return paths


def fan_out(graph, blackboard, query: str, seeds: List[SeedNode],
            max_hops: int = 3, prune_threshold: float = 0.60,
            max_workers: int = 8) -> List[TracedPath]:
    all_paths: List[TracedPath] = []
    lock = threading.Lock()

    def work(seed: SeedNode):
        ps = trace_from_seed(graph, blackboard, query, seed, max_hops, prune_threshold)
        with lock:
            all_paths.extend(ps)
        blackboard.decay_all()

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, max(1, len(seeds))))) as ex:
        list(ex.map(work, seeds))
    # rank: score + pheromone boost
    for p in all_paths:
        boost = blackboard.pheromone(p.nodes[-1]) * 0.05 if p.nodes else 0.0
        p.score = round(p.score + boost, 4)
    all_paths.sort(key=lambda p: -p.score)
    return all_paths
