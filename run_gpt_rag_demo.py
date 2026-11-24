"""Unified demo: Swarm Intelligence + RAG + GPT agent answering random questions.

Runs:
  1. Phase 1 ingestion (graph + vectors from data_docs/)
  2. Phase 2 swarm trace over a question
  3. Phase 3 GPT RAG synthesis (grounded answer with citations)
  4. Random question agent (answers arbitrary questions)

Usage:
    python run_gpt_rag_demo.py
    # Optional: set OPENAI_API_KEY in .env for GPT-generated answers
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import SETTINGS
from src.llm.gpt_agent import GPTAgent
from src.llm.answer_synthesizer import AnswerSynthesizer
from src.llm.random_question_agent import RandomQuestionAgent
from src.ingestion.pipeline import IngestionPipeline
from src.swarm.workflow import SwarmOrchestrator


def print_header(title: str):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def demo_phase1_ingestion():
    print_header("PHASE 1 — HYBRID INGESTION (Graph + Vectors)")
    pipe = IngestionPipeline(
        graph_backend=SETTINGS.graph_backend,
        embedding_mode="local",
    )
    result = pipe.run(SETTINGS.data_dir)
    print(json.dumps({
        "docs": result["docs"],
        "chunks": result["chunks"],
        "entities": result["entities"],
        "relations": result["relations"],
        "graph_stats": result["graph_stats"],
        "vectors": result["vectors"],
    }, indent=2))
    return pipe


def demo_swarm_trace(pipe, query: str):
    print_header(f"PHASE 2 — SWARM TRACE: '{query}'")
    orch = SwarmOrchestrator(
        pipe.graph, pipe.vectors,
        prune_threshold=SETTINGS.prune_threshold,
        max_hops=SETTINGS.max_hops,
        max_workers=SETTINGS.max_workers,
        top_k_scout=SETTINGS.top_k_scout,
    )
    out = orch.run(query, session_id="demo")
    m = out["metrics"]
    print(f"Latency: {m['latency_s']}s | Visited: {m['visited']} | "
          f"Pruned: {m['pruned']} | Candidates: {m['candidates']} | "
          f"Validated: {m['validated']}")
    print("\nValidated paths:")
    for i, p in enumerate(out["validated"][:5], 1):
        names = p.get("node_names", [])
        edges = p.get("edges", [])
        print(f"  {i}. {' -> '.join(names)}  [{' | '.join(edges)}]  score={p.get('score',0)}")
    return out


def demo_rag_answer(pipe, query: str, gpt_agent: GPTAgent):
    print_header(f"PHASE 3 — GPT RAG ANSWER: '{query}'")
    synth = AnswerSynthesizer(gpt_agent=gpt_agent)
    swarm_out = demo_swarm_trace(pipe, query)
    try:
        hits = pipe.vectors.search(query, top_k=3)
        swarm_out["_vector_hits"] = hits
    except Exception:
        swarm_out["_vector_hits"] = []

    synthesized = synth.synthesize(query, swarm_out, force_gpt=False)
    print(f"\nGPT available: {synthesized.gpt_available}")
    print(f"Used GPT: {synthesized.used_gpt}")
    print(f"Answer:\n{synthesized.answer}")
    print(f"\nSources: {len(synthesized.graph_paths)} graph paths")
    return synthesized


def demo_random_questions(agent: RandomQuestionAgent, count: int = 3):
    print_header(f"PHASE 4 — RANDOM QUESTION AGENT ({count} questions)")
    questions = random.sample(agent.DEFAULT_RANDOM_QUESTIONS, min(count, len(agent.DEFAULT_RANDOM_QUESTIONS)))
    for q in questions:
        res = agent.ask(q, session_id="demo_random")
        print(f"\nQ: {res.question}")
        print(f"  RAG used: {res.used_rag} | GPT used: {res.used_gpt} | "
              f"GPT available: {res.gpt_available}")
        print(f"  Answer: {res.answer[:300]}...")
        print(f"  Metrics: {json.dumps(res.metrics)}")


def main():
    print("Swarm Intelligence + RAG + GPT Agent Demo")
    print("=" * 60)
    print(f"GPT configured: {bool(SETTINGS.openai_api_key)}")
    print(f"Model: {SETTINGS.openai_model}")

    # Phase 1
    pipe = demo_phase1_ingestion()

    # Phase 2 + 3: RAG answer on a graph-grounded question
    gpt_agent = GPTAgent()
    demo_rag_answer(pipe, "Who acquired DeepMind?", gpt_agent)

    # Phase 4: random questions
    agent = RandomQuestionAgent(
        data_dir=SETTINGS.data_dir,
        graph_backend=SETTINGS.graph_backend,
        gpt_agent=gpt_agent,
        auto_ingest=False,  # already ingested above
        pipe=pipe,
    )
    # Reuse the existing pipe/orchestrator
    agent._pipe = pipe
    agent._ingested = True
    agent._orchestrator = SwarmOrchestrator(
        pipe.graph, pipe.vectors,
        prune_threshold=SETTINGS.prune_threshold,
        max_hops=SETTINGS.max_hops,
        max_workers=SETTINGS.max_workers,
        top_k_scout=SETTINGS.top_k_scout,
    )
    demo_random_questions(agent, count=3)

    print_header("DEMO COMPLETE")
    print("Tip: Set OPENAI_API_KEY in .env for GPT-generated grounded answers.")


if __name__ == "__main__":
    main()