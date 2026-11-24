"""Phase 3 acceptance tests — GPT + RAG agent (F-03).

Tests run without an OpenAI API key (graceful fallback to evidence summary).
When OPENAI_API_KEY is set, GPT-powered answers are also verified.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.llm.gpt_agent import GPTAgent, GPTConfig
from src.llm.answer_synthesizer import AnswerSynthesizer, SynthesizedAnswer
from src.llm.random_question_agent import RandomQuestionAgent, RandomQuestionResult
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.loaders import ensure_sample_docs


def test_gpt_agent_unavailable_without_key(tmp_path):
    """Without OPENAI_API_KEY, GPTAgent should report unavailable."""
    agent = GPTAgent(config=GPTConfig(api_key=""))
    assert agent.available is False
    assert agent.chat([{"role": "user", "content": "hello"}]) is None


def test_gpt_agent_config_defaults():
    cfg = GPTConfig(api_key="test-key")
    from config import SETTINGS
    assert cfg.model == SETTINGS.openai_model
    assert cfg.temperature == 0.3
    assert cfg.max_tokens == 800


def test_synthesizer_fallback_without_gpt(tmp_path):
    """AnswerSynthesizer should produce an evidence-summary answer without GPT."""
    ensure_sample_docs(tmp_path)
    pipe = IngestionPipeline()
    pipe.run(tmp_path)

    agent = GPTAgent(config=GPTConfig(api_key=""))  # no key
    synth = AnswerSynthesizer(gpt_agent=agent)
    assert synth.gpt.available is False

    swarm_out = {
        "validated": [
            {
                "node_names": ["Google", "DeepMind"],
                "edges": ["ACQUIRED"],
                "score": 0.85,
                "hops": 1,
                "evidence_chunks": ["chunk_1"],
            }
        ],
        "candidates": [],
        "seeds": [{"name": "Google", "node_id": "ent_abc"}],
        "metrics": {"visited": 3, "pruned": 0, "validated": 1, "latency_s": 0.5},
        "_vector_hits": [],
    }
    result = synth.synthesize("Who acquired DeepMind?", swarm_out)
    assert isinstance(result, SynthesizedAnswer)
    assert result.used_gpt is False
    assert result.gpt_available is False
    assert "DeepMind" in result.answer or "Google" in result.answer
    assert len(result.graph_paths) == 1


def test_synthesizer_answers_from_general_knowledge_without_evidence():
    class AvailableGPT:
        available = True

        def __init__(self):
            self.prompt = ""

        def complete(self, prompt, system_prompt=None):
            self.prompt = prompt
            return "Paris is the capital of France. (General knowledge)"

    agent = AvailableGPT()
    synth = AnswerSynthesizer(gpt_agent=agent)
    result = synth.synthesize("What is the capital of France?", {
        "validated": [],
        "candidates": [],
        "seeds": [],
        "metrics": {},
        "_vector_hits": [],
    })

    assert result.used_gpt is True
    assert "Paris is the capital" in result.answer
    assert "general knowledge" in agent.prompt


def test_random_question_agent_without_gpt(tmp_path):
    """RandomQuestionAgent should work without GPT (evidence summary fallback)."""
    ensure_sample_docs(tmp_path)
    agent = RandomQuestionAgent(
        data_dir=str(tmp_path),
        gpt_agent=GPTAgent(config=GPTConfig(api_key="")),
        auto_ingest=True,
    )
    res = agent.ask("Who acquired DeepMind?", session_id="t1")
    assert isinstance(res, RandomQuestionResult)
    assert res.question == "Who acquired DeepMind?"
    assert len(res.answer) > 0
    assert res.gpt_available is False


def test_random_question_agent_ask_random(tmp_path):
    ensure_sample_docs(tmp_path)
    agent = RandomQuestionAgent(
        data_dir=str(tmp_path),
        gpt_agent=GPTAgent(config=GPTConfig(api_key="")),
        auto_ingest=True,
    )
    res = agent.ask_random(session_id="t2")
    assert res.question in agent.DEFAULT_RANDOM_QUESTIONS
    assert len(res.answer) > 0


def test_random_question_agent_ask_many(tmp_path):
    ensure_sample_docs(tmp_path)
    agent = RandomQuestionAgent(
        data_dir=str(tmp_path),
        gpt_agent=GPTAgent(config=GPTConfig(api_key="")),
        auto_ingest=True,
    )
    results = agent.ask_many(["Who acquired DeepMind?", "Where is MIT located?"], session_id="t3")
    assert len(results) == 2
    assert results[0].question == "Who acquired DeepMind?"
    assert results[1].question == "Where is MIT located?"


def test_synthesized_answer_dataclass_defaults():
    sa = SynthesizedAnswer(answer="hello")
    assert sa.answer == "hello"
    assert sa.used_gpt is False
    assert sa.gpt_available is False
    assert sa.graph_paths == []
    assert sa.sources == []
    assert sa.metrics == {}