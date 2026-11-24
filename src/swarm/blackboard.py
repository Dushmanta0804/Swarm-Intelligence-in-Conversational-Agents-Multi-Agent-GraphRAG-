"""Shared Blackboard Memory — stigmergy layer (Redis in arch, local-first now)."""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@dataclass
class AgentEvent:
    t: float
    agent: str
    action: str
    detail: Dict[str, Any] = field(default_factory=dict)


class Blackboard:
    """Visited tracking + pheromone-weighted scoring with Redis mirror.

    Phase 5: mirrors all stigmergy into a spec-compliant BlackboardState
    (memory.md §2) and evaporates with ρ=0.15 per §3.2.
    """

    def __init__(self, query_id: str, decay: float = 0.85, deposit: float = 1.0,
                 redis_client=None, redis_prefix: str = "swarm:bb:",
                 original_prompt: str = "", evaporation: float = 0.15):
        self.query_id = query_id
        self.decay = decay
        self.deposit_amount = deposit
        self.evaporation = evaporation
        self._lock = threading.Lock()
        self.visited: Dict[str, float] = {}
        self.pheromones: Dict[str, float] = {}
        self.pruned: Dict[str, str] = {}
        self.paths: List[Dict[str, Any]] = []
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.trail: List[AgentEvent] = []
        self._redis = redis_client
        self._rprefix = f"{redis_prefix}{query_id}:"
        # spec §2 mirror (lazy import to avoid cycles)
        try:
            from src.swarm.memory import BlackboardState
            self.spec = BlackboardState(query_id=query_id, original_prompt=original_prompt)
        except Exception:
            self.spec = None

    def log(self, agent: str, action: str, **detail):
        ev = AgentEvent(t=time.time(), agent=agent, action=action, detail=detail)
        with self._lock:
            self.trail.append(ev)
        if self._redis is not None:
            try:
                self._redis.rpush(self._rprefix + "trail", f"{ev.t}|{agent}|{action}|{detail}")
            except Exception:
                pass
        return ev

    def is_visited(self, node_id: str) -> bool:
        with self._lock:
            hit = node_id in self.visited
        if not hit and self._redis is not None:
            try:
                hit = bool(self._redis.sismember(self._rprefix + "visited", node_id))
            except Exception:
                pass
        return hit

    def mark_visited(self, node_id: str, agent: str = "?"):
        with self._lock:
            first = node_id not in self.visited
            self.visited[node_id] = time.time()
        if self._redis is not None:
            try:
                self._redis.sadd(self._rprefix + "visited", node_id)
            except Exception:
                pass
        if first:
            self.log(agent, "visited", node=node_id)

    def deposit(self, node_id: str, amount: Optional[float] = None, agent: str = "?"):
        """Spec §3.1: τ(N_i) = 1.0 on visit (clamped to [0,1])."""
        amt = self.deposit_amount if amount is None else amount
        with self._lock:
            self.pheromones[node_id] = min(1.0, self.pheromones.get(node_id, 0.0) + amt)
            level = self.pheromones[node_id]
            # mirror into spec state
            if self.spec is not None:
                try:
                    self.spec.deposit(node_id, agent, intensity=level)
                except Exception:
                    pass
        if self._redis is not None:
            try:
                self._redis.zincrby(self._rprefix + "pheromones", amt, node_id)
            except Exception:
                pass
        self.log(agent, "pheromone_deposit", node=node_id, amount=amt, level=round(level, 3))

    def decay_all(self, rho: Optional[float] = None):
        """Spec §3.2: τ(t) = τ(t-1) × (1 − ρ), ρ = 0.15 default."""
        r = self.evaporation if rho is None else rho
        with self._lock:
            for k in list(self.pheromones.keys()):
                self.pheromones[k] = round(self.pheromones[k] * (1 - r), 6)
                if self.pheromones[k] < 1e-6 and k not in self.pruned:
                    del self.pheromones[k]
            if self.spec is not None:
                try:
                    self.spec.evaporate(rho=r)
                except Exception:
                    pass

    def pheromone(self, node_id: str) -> float:
        with self._lock:
            return self.pheromones.get(node_id, 0.0)

    def mark_pruned(self, node_id: str, reason: str, agent: str = "?"):
        with self._lock:
            self.pruned[node_id] = reason
        self.log(agent, "pruned", node=node_id, reason=reason)

    def blacklist_dead_end(self, node_id: str, agent: str = "?"):
        """Spec §3.1: dead end → τ = 0.0 + blacklisted."""
        with self._lock:
            self.pheromones[node_id] = 0.0
            self.pruned[node_id] = "dead_end"
            if self.spec is not None:
                try:
                    self.spec.blacklist_dead_end(node_id, agent)
                except Exception:
                    pass
        self.log(agent, "dead_end_blacklisted", node=node_id)

    def record_edge(self, source: str, target: str, relation: str,
                    confidence: float, agent: str = "?"):
        if self.spec is not None:
            try:
                self.spec.record_edge(source, target, relation, confidence)
            except Exception:
                pass

    def add_path(self, path: Dict[str, Any]):
        with self._lock:
            self.paths.append(path)
        self.log("validator", "path_accepted", nodes=path.get("nodes"), score=path.get("score"))

    def register(self, agent_id: str, role: str, **info):
        with self._lock:
            self.active_agents[agent_id] = {"role": role, **info, "alive": True}
        self.log(role, "registered", agent_id=agent_id, **info)

    def deregister(self, agent_id: str):
        with self._lock:
            if agent_id in self.active_agents:
                self.active_agents[agent_id]["alive"] = False

    def reset_query(self):
        with self._lock:
            self.visited.clear(); self.pheromones.clear(); self.pruned.clear()
            self.paths.clear(); self.active_agents.clear(); self.trail.clear()
        if self._redis is not None:
            try:
                for k in self._redis.keys(self._rprefix + "*"):
                    self._redis.delete(k)
            except Exception:
                pass

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "query_id": self.query_id,
                "visited": len(self.visited),
                "pruned": len(self.pruned),
                "paths": len(self.paths),
                "active_agents": len([a for a in self.active_agents.values() if a.get("alive")]),
                "top_pheromones": sorted(self.pheromones.items(), key=lambda x: -x[1])[:10],
                "events": len(self.trail),
            }


def make_blackboard(query_id: str) -> "Blackboard":
    """Redis-backed when USE_REDIS=true and reachable, else local."""
    from config import SETTINGS
    client = None
    if SETTINGS.use_redis:
        try:
            import redis
            client = redis.Redis.from_url(SETTINGS.redis_url, socket_connect_timeout=2)
            client.ping()
        except Exception as e:
            print(f"[blackboard] redis unavailable, local fallback: {e}")
            client = None
    return Blackboard(query_id, decay=SETTINGS.pheromone_decay,
                      deposit=SETTINGS.pheromone_deposit, redis_client=client)

