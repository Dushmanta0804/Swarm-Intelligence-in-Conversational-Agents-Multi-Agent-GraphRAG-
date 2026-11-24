"""Random Question Agent — answers arbitrary/random questions using RAG + GPT."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import SETTINGS
from src.ingestion.pipeline import IngestionPipeline
from src.llm.answer_synthesizer import AnswerSynthesizer, SynthesizedAnswer
from src.llm.gpt_agent import GPTAgent
from src.swarm.workflow import SwarmOrchestrator


@dataclass
class RandomQuestionResult:
    question: str
    answer: str
    used_rag: bool
    used_gpt: bool
    gpt_available: bool
    swarm_output: Dict[str, Any] = field(default_factory=dict)
    synthesized: Optional[SynthesizedAnswer] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class RandomQuestionAgent:
    DEFAULT_RANDOM_QUESTIONS: List[str] = [
        "Who acquired DeepMind?",
        "What is the relationship between Microsoft and OpenAI?",
        "Where is MIT located?",
        "Tell me about shell company transfers from Acme Holdings",
        "Who leads the Swarm Lab at MIT?",
        "What is swarm intelligence?",
        "Explain GraphRAG in simple terms",
        "How do pheromones work in ant colonies?",
        "What is the capital of France?",
        "Who won the 2022 FIFA World Cup?",
    ]

    def __init__(
        self,
        data_dir: str = "data_docs",
        graph_backend: str = "local",
        embedding_mode: str = "local",
        gpt_agent: Optional[GPTAgent] = None,
        synthesizer: Optional[AnswerSynthesizer] = None,
        auto_ingest: bool = True,
        pipe: Optional[IngestionPipeline] = None,
    ):
        self.data_dir = data_dir
        self.graph_backend = graph_backend
        self.embedding_mode = embedding_mode
        self.gpt = gpt_agent or GPTAgent()
        self.synth = synthesizer or AnswerSynthesizer(gpt_agent=self.gpt)
        self._pipe: Optional[IngestionPipeline] = pipe
        self._orchestrator: Optional[SwarmOrchestrator] = None
        self._ingested = pipe is not None
        if auto_ingest and pipe is None:
            self.ensure_ingested()

    # ---- lifecycle ----
    def ensure_ingested(self) -> bool:
        """Run ingestion once (idempotent) so the graph + vectors exist."""
        if self._ingested:
            return True
        try:
            self._pipe = IngestionPipeline(
                graph_backend=self.graph_backend,
                embedding_mode=self.embedding_mode,
            )
            ing = self._pipe.run(self.data_dir)
            self._orchestrator = SwarmOrchestrator(
                self._pipe.graph,
                self._pipe.vectors,
                prune_threshold=SETTINGS.prune_threshold,
                max_hops=SETTINGS.max_hops,
                max_workers=SETTINGS.max_workers,
                top_k_scout=SETTINGS.top_k_scout,
            )
            self._ingested = True
            print(f"[random_agent] ingested: {ing['entities']} entities, {ing['relations']} relations")
            return True
        except Exception as e:
            print(f"[random_agent] ingestion failed: {e}")
            self._ingested = False
            return False

    def _run_swarm(self, query: str, session_id: str = "random_agent") -> Dict[str, Any]:
        if self._orchestrator is None:
            self.ensure_ingested()
        assert self._orchestrator is not None
        out = self._orchestrator.run(query, session_id=session_id)
        try:
            hits = self._pipe.vectors.search(query, top_k=3) if self._pipe else []
            out["_vector_hits"] = hits
        except Exception:
            out["_vector_hits"] = []
        return out

    # ---- public API ----
    def ask(self, question: str, session_id: str = "random_agent") -> RandomQuestionResult:
        """Answer a single (possibly random) question."""
        import time

        t0 = time.time()
        if not self._ingested:
            self.ensure_ingested()

        swarm_out = self._run_swarm(question, session_id=session_id)
        synthesized = self.synth.synthesize(question, swarm_out, force_gpt=False)

        validated = swarm_out.get("validated", []) or []
        candidates = swarm_out.get("candidates", []) or []
        used_rag = bool(validated or candidates) and self.gpt.available

        if not synthesized.answer or synthesized.answer.strip() == "":
            if self.gpt.available:
                gen = self.gpt.complete(
                    prompt=f"Answer this question concisely: {question}",
                    system_prompt="You are a helpful assistant. Answer concisely.",
                )
                synthesized.answer = gen or "I don't have enough information to answer that."
                synthesized.used_gpt = True
            else:
                synthesized.answer = (
                    "I couldn't find relevant evidence in the knowledge graph, and no GPT API key "
                    "is configured. Please add an OPENAI_API_KEY to .env to enable GPT-powered "
                    "answers for random questions."
                )

        dt = time.time() - t0
        return RandomQuestionResult(
            question=question,
            answer=synthesized.answer,
            used_rag=used_rag,
            used_gpt=synthesized.used_gpt,
            gpt_available=self.gpt.available,
            swarm_output=swarm_out,
            synthesized=synthesized,
            metrics={
                "latency_s": round(dt, 3),
                "swarm_validated": len(validated),
                "swarm_candidates": len(candidates),
                "swarm_latency_s": swarm_out.get("metrics", {}).get("latency_s", 0),
            },
        )

    def ask_random(self, session_id: str = "random_agent") -> RandomQuestionResult:
        """Pick a random question from the default list and answer it."""
        import random

        q = random.choice(self.DEFAULT_RANDOM_QUESTIONS)
        return self.ask(q, session_id=session_id)

    def ask_many(self, questions: List[str], session_id: str = "random_agent") -> List[RandomQuestionResult]:
        """Answer a list of questions sequentially."""
        return [self.ask(q, session_id=session_id) for q in questions]