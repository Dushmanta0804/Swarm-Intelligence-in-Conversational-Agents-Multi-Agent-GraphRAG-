"""Swarm Orchestrator — LangGraph-core state machine (local runnable, LangGraph-ready)."""
from __future__ import annotations
import time
import uuid
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.swarm.state import SwarmState
from src.swarm.blackboard import Blackboard, make_blackboard
from src.swarm.agents import dispatcher, scout, tracer, validator


class SwarmOrchestrator:
    """Pipeline: dispatch -> scout (focus-first) -> trace(fan-out) -> validate."""

    def __init__(self, graph, vectors, blackboard: Optional[Blackboard] = None,
                 prune_threshold: float = 0.60, max_hops: int = 3,
                 max_workers: int = 8, top_k_scout: int = 5,
                 on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
                 session_memory=None):
        self.graph = graph
        self.vectors = vectors
        self.prune_threshold = prune_threshold
        self.max_hops = max_hops
        self.max_workers = max_workers
        self.top_k_scout = top_k_scout
        self.on_event = on_event
        self._external_bb = blackboard
        if session_memory is None:
            try:
                from src.swarm.session_memory import make_session_memory
                session_memory = make_session_memory()
            except Exception:
                session_memory = None
        self._session_memory = session_memory

    def _emit(self, **ev):
        if self.on_event:
            try:
                self.on_event(ev)
            except Exception:
                pass

    def run(self, query: str, query_id: Optional[str] = None,
            session_id: str = "default") -> Dict[str, Any]:
        t0 = time.time()
        qid = query_id or f"q_{uuid.uuid4().hex[:8]}"
        bb = self._external_bb or make_blackboard(qid)
        try:
            if getattr(bb, "spec", None) is not None:
                bb.spec.original_prompt = query
                bb.spec.query_id = qid
        except Exception:
            pass
        state = SwarmState(query=query, query_id=qid)
        bb.register("dispatcher_0", "dispatcher")
        state.sub_goals = dispatcher.decompose(query)
        # Phase 5 §4: dispatcher checks focus cache BEFORE global search
        focus_hit = None
        if self._session_memory is not None:
            try:
                focus_hit = self._session_memory.lookup_focus(session_id, query)
            except Exception:
                focus_hit = None
        bb.log("dispatcher", "decomposed", goals=[g.question for g in state.sub_goals],
               focus_hit=bool(focus_hit and focus_hit.get("hit")))
        self._emit(stage="dispatched", goals=[g.model_dump() for g in state.sub_goals],
                   focus_hit=focus_hit)
        bb.deregister("dispatcher_0")
        bb.register("scout_0", "scout")
        seen, seeds = set(), []
        if focus_hit and focus_hit.get("hit"):
            # anchor immediately to cached coordinates — skip global vector search
            from src.swarm.state import SeedNode
            for n in focus_hit["nodes"]:
                nid = n.get("id")
                if nid and nid not in seen:
                    seen.add(nid)
                    seeds.append(SeedNode(node_id=nid, name=n.get("name", nid),
                                          anchor_score=0.99, source="focus-cache"))
                    bb.mark_visited(nid, agent="scout")
            bb.log("scout", "focus_anchored", nodes=[s.node_id for s in seeds],
                   skipped_global_search=True)
        else:
            for g in state.sub_goals:
                for s in scout.anchor(self.graph, self.vectors, g.question,
                                      seed_hints=g.seed_entities, top_k=self.top_k_scout):
                    if s.node_id not in seen:
                        seen.add(s.node_id)
                        seeds.append(s)
                        bb.mark_visited(s.node_id, agent="scout")
        seeds.sort(key=lambda s: -s.anchor_score)
        state.seeds = seeds[: self.top_k_scout * 2]
        bb.log("scout", "anchored", seeds=[s.model_dump() for s in state.seeds])
        self._emit(stage="anchored", seeds=[s.model_dump() for s in state.seeds])
        bb.deregister("scout_0")
        cands = tracer.fan_out(self.graph, bb, query, state.seeds,
                               max_hops=self.max_hops,
                               prune_threshold=self.prune_threshold,
                               max_workers=self.max_workers)
        state.candidate_paths = cands
        state.pruned_count = len(bb.pruned)
        self._emit(stage="traced", candidates=len(cands), pruned=len(bb.pruned))
        bb.register("validator_0", "validator")
        state.validated_paths = validator.validate(cands, bb)
        bb.deregister("validator_0")
        self._emit(stage="validated", validated=len(state.validated_paths))
        dt = time.time() - t0
        state.metrics = {
            "latency_s": round(dt, 3),
            "visited": len(bb.visited),
            "pruned": len(bb.pruned),
            "candidates": len(state.candidate_paths),
            "validated": len(state.validated_paths),
            "llm_calls": 0,
            "blackboard": bb.snapshot(),
        }
        # Phase 5 §4: cache top-k focus for follow-up turns
        focus_cached = False
        try:
            if self._session_memory is not None:
                focus_nodes = [{"id": p["nodes"][-1] if p.get("nodes") else "",
                                "name": (p.get("node_names") or [""])[-1],
                                "score": p.get("score", 0)}
                               for p in ([v.model_dump() for v in state.validated_paths]
                                         or [p.model_dump() for p in state.candidate_paths])]
                self._session_memory.store_focus(session_id, focus_nodes, query, qid)
                focus_cached = True
        except Exception:
            pass
        state.metrics["focus_cached"] = focus_cached
        state.metrics["focus_hit"] = bool(focus_hit and focus_hit.get("hit"))
        return {
            "query_id": qid,
            "session_id": session_id,
            "focus_hit": focus_hit,
            "sub_goals": [g.model_dump() for g in state.sub_goals],
            "seeds": [s.model_dump() for s in state.seeds],
            "candidates": [p.model_dump() for p in state.candidate_paths],
            "validated": [p.model_dump() for p in state.validated_paths],
            "metrics": state.metrics,
            "trail": [{"t": e.t, "agent": e.agent, "action": e.action, "detail": e.detail}
                      for e in bb.trail[-100:]],
        }

    def langgraph_app(self):
        """Optional compiled LangGraph mirror of run() stages."""
        from langgraph.graph import StateGraph, END

        def n_dispatch(s):
            s["sub_goals"] = dispatcher.decompose(s["query"])
            return s

        def n_scout(s):
            seeds, seen = [], set()
            for goal in s["sub_goals"]:
                q = goal.question if hasattr(goal, "question") else goal["question"]
                hints = goal.seed_entities if hasattr(goal, "seed_entities") else goal.get("seed_entities", [])
                for sd in scout.anchor(self.graph, self.vectors, q, hints, self.top_k_scout):
                    if sd.node_id not in seen:
                        seen.add(sd.node_id); seeds.append(sd)
            s["seeds"] = seeds
            return s

        def n_trace(s):
            s["candidates"] = tracer.fan_out(self.graph, s["_bb"], s["query"], s["seeds"],
                                             self.max_hops, self.prune_threshold, self.max_workers)
            return s

        def n_validate(s):
            s["validated"] = validator.validate(s["candidates"], s["_bb"])
            return s

        g = StateGraph(dict)
        g.add_node("dispatch", n_dispatch)
        g.add_node("scout", n_scout)
        g.add_node("trace", n_trace)
        g.add_node("validate", n_validate)
        g.set_entry_point("dispatch")
        g.add_edge("dispatch", "scout")
        g.add_edge("scout", "trace")
        g.add_edge("trace", "validate")
        g.add_edge("validate", END)
        return g.compile()
