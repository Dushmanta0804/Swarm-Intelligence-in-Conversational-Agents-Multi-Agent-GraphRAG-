"""Validator Agent — resolves conflicting edges, cross-checks factual consistency."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import sys
from typing import List
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.swarm.state import TracedPath

# conflicting relation pairs (A vs B between same node pair = contradiction)
CONFLICTS = {
    frozenset({"OWNS", "DOES_NOT_OWN"}),
    frozenset({"LOCATED_IN"}),
    frozenset({"ACQUIRED", "SOLD"}),
}


def validate(paths: List[TracedPath], blackboard, min_score: float = 0.3) -> List[TracedPath]:
    ok: List[TracedPath] = []
    seen_edges: dict[tuple, List[str]] = defaultdict(list)
    for p in paths:
        if p.score < min_score or p.pruned:
            continue
        # pairwise edge conflict check
        bad = False
        for i, e in enumerate(p.edges):
            a = p.node_names[i] if i < len(p.node_names) else ""
            b = p.node_names[i + 1] if i + 1 < len(p.node_names) else ""
            key = (a, b)
            for prev in seen_edges.get(key, []):
                if frozenset({prev, e}) in CONFLICTS and prev != e:
                    bad = True
                    blackboard.log("validator", "conflict_resolved",
                                   edge_a=prev, edge_b=e, nodes=[a, b],
                                   kept=max(prev, e, key=len))
                    break
            seen_edges[key].append(e)
            if bad:
                break
        if bad:
            continue
        # dedupe identical node sequences
        sig = tuple(p.node_names)
        if any(tuple(q.node_names) == sig for q in ok):
            blackboard.log("validator", "duplicate_dropped", nodes=p.node_names)
            continue
        ok.append(p)
        blackboard.add_path({"nodes": p.node_names, "edges": p.edges,
                             "score": p.score, "evidence": p.evidence_chunks})
    return ok
