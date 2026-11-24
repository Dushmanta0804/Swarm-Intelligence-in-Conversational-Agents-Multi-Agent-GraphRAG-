"""LLM / GPT agent layer for Swarm Intelligence GraphRAG.

Provides:
- GPTAgent: OpenAI-backed chat/completion client with retry + token budgeting
- AnswerSynthesizer: combines swarm evidence (graph paths + vector chunks) with GPT
  to produce grounded, cited answers
- RandomQuestionAgent: answers arbitrary/random questions using RAG + GPT fallback
"""
from src.llm.gpt_agent import GPTAgent, GPTConfig
from src.llm.answer_synthesizer import AnswerSynthesizer, SynthesizedAnswer
from src.llm.random_question_agent import RandomQuestionAgent

__all__ = ["GPTAgent", "GPTConfig", "AnswerSynthesizer", "SynthesizedAnswer", "RandomQuestionAgent"]