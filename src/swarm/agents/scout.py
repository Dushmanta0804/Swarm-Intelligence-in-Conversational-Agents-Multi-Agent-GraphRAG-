"""Scout Agent — anchors queries to entry nodes via hybrid vector + lexical matching."""
from __future__ import annotations
import re
from pathlib import Path
import sys
from typing import List
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.swarm.state import SeedNode


def _lexical_score(query: str, name: str) -> float:
    qt = set(re.findall(r"[a-z0-9]+", query.lower()))
    nt = set(re.findall(r"[a-z0-9]+", name.lower()))
    if not qt or not nt:
        return 0.0
    return len(qt & nt) / max(1, len(qt | nt))


def anchor(graph, vectors, query: str, seed_hints: List[str] | None = None,
           top_k: int = 5) -> List[SeedNode]:
    seed_hints = seed_hints or []
    cands: dict[str, dict] = {}
    # 1) vector-driven: chunks -> graph names mentioned in chunk text
    try:
        hits = vectors.search(query, top_k=top_k)
    except Exception:
        hits = []
    for chunk, vscore in hits:
        text_low = chunk.text.lower()
        for node in _all_nodes(graph):
            nid, name = node["id"], node.get("name", "")
            if name and name.lower() in text_low:
                prev = cands.get(nid, {"name": name, "v": 0.0, "chunk": None})
                if vscore > prev["v"]:
                    prev.update({"v": vscore, "chunk": chunk.chunk_id})
                cands[nid] = prev
    # 2) lexical: direct name match on query + seed hints
    probes = [query] + list(seed_hints)
    for probe in probes:
        try:
            found = graph.find_by_name(probe)
        except Exception:
            found = []
        for n in found:
            nid = n.get("id")
            if not nid:
                continue
            prev = cands.get(nid, {"name": n.get("name", ""), "v": 0.0, "chunk": None})
            prev["lex"] = max(prev.get("lex", 0.0), _lexical_score(probe, n.get("name", "")))
            cands[nid] = prev
    # hybrid fuse
    seeds: List[SeedNode] = []
    for nid, info in cands.items():
        lex = info.get("lex", 0.0)
        if lex == 0.0 and info["name"]:
            lex = _lexical_score(query, info["name"])
        score = 0.65 * info.get("v", 0.0) + 0.35 * lex
        src = "vector+lexical" if info.get("v", 0) > 0 and lex > 0 else (
            "vector" if info.get("v", 0) > 0 else "lexical")
        seeds.append(SeedNode(node_id=nid, name=info["name"],
                              anchor_score=round(score, 4), source=src,
                              chunk_id=info.get("chunk")))
    seeds.sort(key=lambda s: -s.anchor_score)
    return seeds[:top_k]


def _all_nodes(graph) -> List[dict]:
    if getattr(graph, "backend", "local") == "local":
        return [{"id": n, **d} for n, d in graph._g.nodes(data=True)]
    try:
        return graph.find_by_name("")
    except Exception:
        return []
