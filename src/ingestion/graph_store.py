"""Property-graph store: local NetworkX backend + Neo4j interface (Phase 4 ready)."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.models import Entity, Relation


class GraphStore:
    """Unified interface. backend='local' works now; backend='neo4j' activates when configured."""

    def __init__(self, backend: str = "local", persist_path: Optional[str] = None):
        self.backend = backend
        self.persist_path = persist_path
        if backend == "local":
            import networkx as nx
            self._g = nx.MultiDiGraph()
        elif backend == "neo4j":
            from config import SETTINGS
            try:
                from neo4j import GraphDatabase
            except ImportError as e:
                raise ImportError("pip install neo4j to use GRAPH_BACKEND=neo4j") from e
            self._driver = GraphDatabase.driver(SETTINGS.neo4j_uri,
                                                auth=(SETTINGS.neo4j_user, SETTINGS.neo4j_password))
        else:
            raise ValueError(f"unknown graph backend {backend}")

    # ---- writes ----
    def upsert_entities(self, entities: List[Entity]):
        if self.backend == "local":
            for e in entities:
                self._g.add_node(e.entity_id, name=e.name, type=e.type, **e.metadata)
        else:
            with self._driver.session() as s:
                for e in entities:
                    s.run("MERGE (n:Entity {id:$id}) SET n.name=$name, n.type=$type",
                          id=e.entity_id, name=e.name, type=e.type)

    def upsert_relations(self, relations: List[Relation]):
        if self.backend == "local":
            for r in relations:
                self._g.add_edge(r.source, r.target, type=r.type,
                                 confidence=r.confidence,
                                 evidence_chunk_id=r.evidence_chunk_id or "")
        else:
            with self._driver.session() as s:
                for r in relations:
                    s.run("MATCH (a:Entity {id:$s}),(b:Entity {id:$t}) "
                          "MERGE (a)-[rel:REL {type:$type}]->(b) "
                          "SET rel.confidence=$c",
                          s=r.source, t=r.target, type=r.type, c=r.confidence)

    # ---- reads (used by Phase 2 swarm) ----
    def neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        if self.backend == "local":
            out = []
            if entity_id not in self._g:
                return out
            for _, tgt, data in self._g.out_edges(entity_id, data=True):
                out.append({"target": tgt, **self._g.nodes[tgt], **data})
            for src, _, data in self._g.in_edges(entity_id, data=True):
                out.append({"target": src, **self._g.nodes[src], **data, "direction": "in"})
            return out
        with self._driver.session() as s:
            recs = s.run("MATCH (a:Entity {id:$id})-[r]-(b) RETURN b.id as id,b.name as name,r.type as t LIMIT 50",
                         id=entity_id)
            return [dict(r) for r in recs]

    def stats(self) -> Dict[str, int]:
        if self.backend == "local":
            return {"nodes": self._g.number_of_nodes(), "edges": self._g.number_of_edges()}
        with self._driver.session() as s:
            n = s.run("MATCH (n:Entity) RETURN count(n) as c").single()["c"]
            e = s.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
            return {"nodes": n, "edges": e}

    def export_json(self, path: str | Path):
        path = Path(path)
        if self.backend == "local":
            import networkx as nx
            data = nx.node_link_data(self._g, edges="links")
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        else:
            path.write_text(json.dumps(self.stats()), encoding="utf-8")

    def find_by_name(self, name: str) -> List[Dict[str, Any]]:
        if self.backend == "local":
            q = name.strip().lower()
            return [{"id": n, **d} for n, d in self._g.nodes(data=True)
                    if q in d.get("name", "").lower() or d.get("name", "").lower() in q]
        with self._driver.session() as s:
            recs = s.run("MATCH (n:Entity) WHERE toLower(n.name) CONTAINS toLower($q) RETURN n.id as id,n.name as name LIMIT 10", q=name)
            return [dict(r) for r in recs]
