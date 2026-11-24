"""Schema-guided entity/relation extraction.

Phase 1: deterministic local extractor (regex + patterns) — zero API key needed.
Phase 2+: plug an LLM extractor via `LLMExtractorHook.extract()` without changing pipeline.
"""
from __future__ import annotations
import re
from pathlib import Path
import sys
from typing import List, Tuple
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.models import Chunk, Entity, Relation, make_id


ENTITY_TYPES = ["ORG", "PERSON", "LOCATION", "CONCEPT", "EVENT"]

# explicit org gazetteer for reliable demo extraction
KNOWN_ORGS = [
    "Alphabet Inc.", "Google", "DeepMind", "MIT", "Swarm Lab",
    "Microsoft", "OpenAI", "Acme Holdings", "Beacon Ltd", "Cedar Trust",
]

REL_PATTERNS = [
    (re.compile(r"(\b[\w .&'-]+?)\s+acquired\s+(\b[\w .&'-]+?)(?:\s+in\s+\d{4})?[.\n]", re.I), "ACQUIRED"),
    (re.compile(r"(\b[\w .&'-]+?)\s+collaborates?\s+with\s+(\b[\w .&'-]+?)[.\n]", re.I), "COLLABORATES_WITH"),
    (re.compile(r"(\b[\w .&'-]+?)\s+partners?\s+with\s+(\b[\w .&'-]+?)[.\n]", re.I), "PARTNERS_WITH"),
    (re.compile(r"(\b[\w .&'-]+?)\s+leads?\s+the\s+(\b[\w .&'-]+?)[.\n]", re.I), "LEADS"),
    (re.compile(r"(\b[\w .&'-]+?)\s+published\s+a\s+paper\s+on\s+([\w \-]+?)[.\n]", re.I), "PUBLISHED_ON"),
    (re.compile(r"(\b[\w .&'-]+?)\s+is\s+located\s+in\s+(\b[\w .&'-]+?)[.\n]", re.I), "LOCATED_IN"),
    (re.compile(r'"name":\s*"([^"]+)"\s*,\s*"owns":\s*"([^"]+)"', re.I), "OWNS"),
    (re.compile(r'"name":\s*"([^"]+)"\s*,\s*"transfers_to":\s*"([^"]+)"', re.I), "TRANSFERS_TO"),
]

PERSON_RE = re.compile(r"\bDr\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b|\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
AGENT_RE = re.compile(r"\b(Validator|Scout|Path Tracer|Dispatcher)(?:\s+agents?)?\b", re.I)


def extract_from_chunk(chunk: Chunk) -> Tuple[List[Entity], List[Relation]]:
    text = chunk.text
    entities: dict[str, Entity] = {}
    relations: List[Relation] = []

    def add_entity(name: str, etype: str) -> Entity:
        name = name.strip().strip(",;:")
        if len(name) < 2:
            return None
        eid = make_id("ent", name)
        if eid not in entities:
            entities[eid] = Entity(entity_id=eid, name=name, type=etype,
                                   metadata={"evidence_chunk_id": chunk.chunk_id})
        return entities[eid]

    # known orgs
    for org in KNOWN_ORGS:
        if re.search(r"\b" + re.escape(org) + r"\b", text):
            etype = "ORG"
            if org in ("Swarm Lab",):
                etype = "ORG"
            add_entity(org, etype)

    # agents as CONCEPT
    for m in AGENT_RE.finditer(text):
        add_entity(m.group(0).strip(), "CONCEPT")

    # persons
    for m in PERSON_RE.finditer(text):
        cand = m.group(0).strip()
        if cand not in entities and len(cand.split()) >= 2 and cand not in KNOWN_ORGS:
            # avoid capturing sentence starts like "Swarm Intelligence"
            if cand in ("Swarm Intelligence", "Path Tracer"):
                continue
            add_entity(cand, "PERSON")

    # locations after "located in"
    for m in re.finditer(r"located in\s+([A-Z][\w\- ]+?)[.\n]", text):
        add_entity(m.group(1).strip(), "LOCATION")

    # relations
    for pattern, rtype in REL_PATTERNS:
        for m in pattern.finditer(text):
            s_raw, t_raw = m.group(1).strip(), m.group(2).strip()
            s = add_entity(s_raw, guess_type(s_raw)) or add_entity(s_raw, "CONCEPT")
            t = add_entity(t_raw, guess_type(t_raw)) or add_entity(t_raw, "CONCEPT")
            if s and t and s.entity_id != t.entity_id:
                relations.append(Relation(source=s.entity_id, target=t.entity_id,
                                          type=rtype, confidence=0.85,
                                          evidence_chunk_id=chunk.chunk_id))
    return list(entities.values()), relations


def guess_type(name: str) -> str:
    if name in KNOWN_ORGS:
        return "ORG"
    if name.startswith("Dr."):
        return "PERSON"
    if re.match(r"^(Validator|Scout|Path Tracer|Dispatcher)", name, re.I):
        return "CONCEPT"
    if name[0:1].isupper() and len(name.split()) <= 2:
        return "ORG"
    return "CONCEPT"


class LLMExtractorHook:
    """Phase 2+ hook: subclass and override extract() to use OpenAI/LLM parsing.

    Example:
        class MyLLM(LLMExtractorHook):
            def extract(self, chunk): ... call LLM, return entities/relations ...
        pipeline = IngestionPipeline(extractor=MyLLM())
    """
    def extract(self, chunk: Chunk):
        return extract_from_chunk(chunk)
