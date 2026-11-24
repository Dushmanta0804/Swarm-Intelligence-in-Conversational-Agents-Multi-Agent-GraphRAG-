# Swarm Intelligence Conversational Agent — Phase 1: Foundation + Hybrid Ingestion
Decentralized multi-hop reasoning over dynamic Knowledge Graphs powered by bio-inspired agent swarms.

## Phase 1 scope (this build)
Implements F-01: Hybrid Knowledge Graph & Vector Store Ingestion
- Upload PDF / Markdown / TXT / JSON
- Schema-guided entity/relation extraction (local, no LLM key required + LLM hook ready)
- Property-graph topology (local NetworkX + Neo4j interface ready)
- Dense text embeddings (local hashed-TF vectors + Qdrant interface ready)
- Entity deduplication + synonym resolution

## Quickstart
```powershell
pip install -r requirements.txt
python run_phase1_demo.py
python -m pytest tests -v
```

## Structure
```
config.py
docker-compose.yml
src/
  ingestion/
    loaders.py
    entity_extractor.py
    deduplicator.py
    graph_store.py
    vector_store.py
    pipeline.py
  models.py
tests/test_phase1.py
run_phase1_demo.py
data_docs/  <- drop your PDFs/MD/TXT/JSON here
```

## Phase roadmap
- Phase 1: Ingestion (THIS)
- Phase 2: Swarm Engine (dispatcher/scout/tracer/pruning/validator)
- Phase 3: Grounded synthesis + citations
- Phase 4: Dual-pane dashboard + visualizer
