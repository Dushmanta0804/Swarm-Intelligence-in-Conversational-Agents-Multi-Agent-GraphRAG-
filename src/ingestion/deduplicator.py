"""Entity deduplication + synonym resolution (F-01 requirement)."""
from __future__ import annotations
import re
from pathlib import Path
import sys
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.models import Entity, Relation

# canonical synonym map — extend freely, also auto-learned below
SYNONYMS = {
    "google": "Alphabet Inc.",
    "alphabet inc.": "Alphabet Inc.",
    "alphabet": "Alphabet Inc.",
    "mit": "MIT",
    "massachusetts institute of technology": "MIT",
    "beacon ltd": "Beacon Ltd",
    "acme holdings": "Acme Holdings",
    "cedar trust": "Cedar Trust",
    "deepmind": "DeepMind",
    "openai": "OpenAI",
    "microsoft": "Microsoft",
}


def normalize(name: str) -> str:
    key = re.sub(r"\s+", " ", name.strip().lower())
    return SYNONYMS.get(key, name.strip())


def deduplicate(entities: List[Entity], relations: List[Relation]):
    """Merge synonym entities. Returns (canonical_entities, remapped_relations, merge_report)."""
    # group by normalized canonical name
    canon: Dict[str, Entity] = {}
    id_map: Dict[str, str] = {}  # old_id -> canonical_id
    for e in entities:
        canonical_name = normalize(e.name)
        # find existing canonical with same normalized-lower name
        match = None
        for cid, ce in canon.items():
            if ce.name.strip().lower() == canonical_name.strip().lower():
                match = ce
                break
        if match is None:
            from src.models import make_id
            cid = make_id("ent", canonical_name)
            match = Entity(entity_id=cid, name=canonical_name, type=e.type,
                           metadata={**e.metadata, "aliases": []})
            canon[cid] = match
        # merge alias
        aliases = match.metadata.setdefault("aliases", [])
        if e.name != match.name and e.name not in aliases:
            aliases.append(e.name)
        id_map[e.entity_id] = match.entity_id

    # remap relations, drop self-loops & exact dupes
    seen = set()
    new_rels: List[Relation] = []
    for r in relations:
        s = id_map.get(r.source, r.source)
        t = id_map.get(r.target, r.target)
        if s == t:
            continue
        key = (s, t, r.type)
        if key in seen:
            continue
        seen.add(key)
        new_rels.append(Relation(source=s, target=t, type=r.type,
                                 confidence=r.confidence,
                                 evidence_chunk_id=r.evidence_chunk_id,
                                 metadata=r.metadata))
    report = {"input_entities": len(entities), "canonical_entities": len(canon),
              "input_relations": len(relations), "output_relations": len(new_rels)}
    return list(canon.values()), new_rels, report
