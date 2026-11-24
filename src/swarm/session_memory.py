"""Phase 5 §4: Multi-turn session memory — Active Focus Sub-Graph cache.

Caches top-k verified nodes per session in Redis for 30 min (TTL).
Follow-up queries intersecting the cached focus anchor immediately,
skipping the global vector search.
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> Set[str]:
    return set(TOKEN_RE.findall(text.lower()))


class SessionMemory:
    """Session-scoped focus cache. Redis when reachable, local dict otherwise."""

    def __init__(self, redis_client=None, top_k: int = 10, ttl_s: int = 1800,
                 prefix: str = "swarm:session:"):
        self._redis = redis_client
        self.top_k = top_k
        self.ttl_s = ttl_s
        self._prefix = prefix
        self._local: Dict[str, Dict[str, Any]] = {}

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}:focus"

    # ---- write: cache top-k verified nodes after each turn ----
    def store_focus(self, session_id: str, nodes: List[Dict[str, Any]],
                    query: str, query_id: str):
        top = nodes[: self.top_k]
        payload = {"query_id": query_id, "query": query,
                   "tokens": sorted(_tokens(query)),
                   "nodes": [{"id": n.get("id") or n.get("node_id"),
                              "name": n.get("name", ""),
                              "score": n.get("score", 0)} for n in top],
                   "stored_at": time.time()}
        if self._redis is not None:
            try:
                self._redis.setex(self._key(session_id), self.ttl_s, json.dumps(payload))
                return payload
            except Exception:
                pass
        self._local[self._key(session_id)] = payload
        return payload

    # ---- read: dispatcher checks intersection before global search ----
    def lookup_focus(self, session_id: str, query: str) -> Optional[Dict[str, Any]]:
        raw = None
        if self._redis is not None:
            try:
                raw = self._redis.get(self._key(session_id))
            except Exception:
                raw = None
        if raw is None:
            raw = self._local.get(self._key(session_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        payload = json.loads(raw) if isinstance(raw, str) else raw
        # TTL check for local mirror
        if time.time() - payload.get("stored_at", 0) > self.ttl_s:
            self.invalidate(session_id)
            return None
        qtokens = _tokens(query)
        cached_tokens = set(payload.get("tokens", []))
        cached_names = " ".join(n.get("name", "") for n in payload.get("nodes", [])).lower()
        overlap = qtokens & cached_tokens
        name_hit = any(t in cached_names for t in qtokens if len(t) > 3)
        if overlap or name_hit:
            return {"hit": True, "overlap": sorted(overlap),
                    "nodes": payload["nodes"], "from_query": payload.get("query"),
                    "skipped_global_search": True}
        return {"hit": False}

    def invalidate(self, session_id: str):
        if self._redis is not None:
            try:
                self._redis.delete(self._key(session_id))
            except Exception:
                pass
        self._local.pop(self._key(session_id), None)


def make_session_memory() -> SessionMemory:
    from config import SETTINGS
    client = None
    if SETTINGS.use_redis:
        try:
            import redis
            client = redis.Redis.from_url(SETTINGS.redis_url, socket_connect_timeout=2)
            client.ping()
        except Exception as e:
            print(f"[session-memory] redis unavailable, local fallback: {e}")
            client = None
    return SessionMemory(redis_client=client, top_k=SETTINGS.focus_cache_top_k,
                         ttl_s=SETTINGS.focus_cache_ttl_s)
