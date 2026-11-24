"""Dispatcher Agent — deconstructs complex prompts into discrete sub-goals + seed entities."""
from __future__ import annotations
import re
import uuid
from pathlib import Path
import sys
from typing import List
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.swarm.state import SubGoal

_SPLIT_RE = re.compile(r"\s+(?:and|then|also|plus|;|\?)\s+", re.I)
_ENTITY_HINT_RE = re.compile(r"\b([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*){0,3})\b")


def decompose(query: str, max_subgoals: int = 3) -> List[SubGoal]:
    parts = [p.strip(" ?.") for p in _SPLIT_RE.split(query.strip()) if p.strip()]
    if not parts:
        parts = [query.strip()]
    parts = parts[:max_subgoals]
    goals: List[SubGoal] = []
    for i, part in enumerate(parts):
        seeds = []
        for m in _ENTITY_HINT_RE.finditer(part):
            cand = m.group(1).strip()
            if len(cand) >= 3 and cand.lower() not in (
                    "how", "what", "which", "when", "where", "does",
                    "affect", "effect", "with", "from", "into"):
                seeds.append(cand)
        words = len(part.split())
        hops = 1 if words <= 6 else (2 if words <= 14 else 3)
        goals.append(SubGoal(id=f"sg_{i}_{uuid.uuid4().hex[:6]}",
                             question=part, seed_entities=seeds[:5],
                             expected_hops=hops))
    return goals
