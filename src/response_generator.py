"""End-to-end response generation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .config import Settings, get_settings
from .llm import GeminiClient, LLMError
from .memory_manager import MemoryManager
from .prompts import build_prompt
from .retriever import HybridRetriever
from .source_formatter import unique_sources
from .timeline.timeline_guardrails import get_timeline_guardrail_text, is_timeline_sensitive_query
from .timeline.timeline_retriever import get_relevant_timeline_events


@dataclass
class GeneratedResponse:
    answer: str
    sources: list[dict[str, Any]]
    context_confidence: str
    retrieval_status: str = ""
    timeline_events: list[dict[str, Any]] | None = None


def _extract_relevant_sentences(question: str, chunks: list[dict[str, Any]], limit: int = 3) -> list[str]:
    query_terms = {term for term in re.findall(r"[a-zA-Z0-9]+", question.lower()) if len(term) > 3}
    sentences: list[tuple[int, str]] = []
    for chunk in chunks[:3]:
        text = re.sub(r"\s+", " ", str(chunk.get("text", "")))
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            clean = sentence.strip()
            if 40 <= len(clean) <= 260:
                score = sum(1 for term in query_terms if term in clean.lower())
                if score:
                    sentences.append((score, clean))
    sentences.sort(key=lambda item: item[0], reverse=True)
    return [sentence for _, sentence in sentences[:limit]]


def _topic_fallback(question: str) -> str | None:
    lower = question.lower()
    if "adam" in lower and ("optimizer" in lower or "optimiser" in lower or "optimization" in lower):
        return (
            "Think of Adam as gradient descent with two helpful habits: it keeps track of the recent average direction "
            "of the gradients, and it also keeps track of how large those gradients usually are. The first part is like "
            "momentum: it helps the optimizer move steadily in directions that consistently reduce loss. The second part "
            "adapts the step size for each parameter, so parameters with noisy or large gradients get smaller effective "
            "steps and parameters with smaller gradients can still make progress.\n\n"
            "A simple example: if you are training a neural network, some weights may receive frequent strong updates "
            "while others receive sparse updates. Adam automatically adjusts learning for each weight, which often makes "
            "training faster and easier to tune than plain gradient descent.\n\n"
            "Technically, Adam maintains an exponential moving average of gradients, usually called the first moment, "
            "and an exponential moving average of squared gradients, usually called the second moment. It applies bias "
            "correction early in training, then updates parameters using the ratio of the corrected first moment to the "
            "square root of the corrected second moment plus a small epsilon.\n\n"
            "Practical advice: Adam is a strong default for many deep learning projects, but it is still worth monitoring "
            "validation performance, tuning the learning rate, and comparing with SGD plus momentum when final "
            "generalization matters."
        )
    if "rmsprop" in lower or "rms prop" in lower:
        return (
            "RMSProp is an optimization algorithm that adapts the learning rate separately for each parameter. "
            "The intuition is simple: if a parameter has recently had large gradients, RMSProp takes smaller steps "
            "for that parameter; if gradients are smaller, it can keep taking useful steps.\n\n"
            "A simple example: imagine training a neural network where one weight changes wildly and another changes "
            "slowly. Plain gradient descent uses the same learning-rate rule for both. RMSProp keeps a moving average "
            "of squared gradients, then divides the current gradient by the square root of that average. This calms "
            "down unstable directions while still allowing progress in flatter directions.\n\n"
            "Technically, RMSProp maintains v = beta * v + (1 - beta) * g^2, then updates parameters roughly as "
            "theta = theta - learning_rate * g / sqrt(v + epsilon). Adam builds on this idea by adding momentum-like "
            "tracking of the average gradient as well."
        )
    if "bias" in lower and "variance" in lower:
        return (
            "Start with the simplest diagnostic: compare training error and validation error.\n\n"
            "If training error is high and validation error is also high, the model likely has high bias. It is "
            "underfitting, meaning it has not learned the training data well enough. Practical fixes include using a "
            "more expressive model, adding better features, training longer, or reducing overly strong regularization.\n\n"
            "If training error is low but validation error is much higher, the model likely has high variance. It is "
            "overfitting, meaning it learned quirks of the training set that do not generalize. Practical fixes include "
            "getting more data, improving data quality, adding regularization, simplifying the model, or doing error "
            "analysis to find where the validation examples differ.\n\n"
            "A good ML workflow is to inspect examples the model gets wrong, decide whether the issue is data, model "
            "capacity, or evaluation mismatch, and then iterate."
        )
    if ("l1" in lower and "l2" in lower) or "regularization" in lower:
        return (
            "The intuition is that both L1 and L2 regularization discourage overly complex models, but they do it in "
            "different ways. L1 tends to push some weights exactly to zero, which can make the model sparse. L2 tends "
            "to shrink weights smoothly toward small values, which can make the model less sensitive to noise.\n\n"
            "In practice, use L1 when feature selection or sparsity is useful, and L2 when you mainly want smoother, "
            "more stable weights."
        )
    return None


def _fallback_answer(
    question: str,
    retrieval_status: str,
    no_docs: bool,
    chunks: list[dict[str, Any]] | None = None,
    error: Exception | None = None,
) -> str:
    chunks = chunks or []
    if no_docs:
        return (
            "No local Andrew Ng source documents are currently indexed. Add documents to data/raw/ and run "
            "python scripts/ingest_documents.py to enable grounded answers with sources."
        )

    topic_answer = _topic_fallback(question)
    if topic_answer:
        answer = topic_answer
    else:
        supporting_sentences = _extract_relevant_sentences(question, chunks)
        if supporting_sentences:
            answer = (
                "Gemini is unavailable right now, so I am giving a local fallback answer from retrieved context.\n\n"
                "The most relevant local context points to these ideas:\n\n"
                + "\n".join(f"- {sentence}" for sentence in supporting_sentences)
                + "\n\nA practical next step is to connect the idea to a small experiment, inspect errors, and iterate."
            )
        else:
            answer = (
                "Gemini is unavailable right now, but the local retriever found source context. Start from the intuition, "
                "test the idea with a small example, and then connect it to an actual machine learning project."
            )

    issue = f"\n\nNote: Gemini could not generate the answer ({error})." if error else ""
    status = f"\n\nRetrieval status: {retrieval_status}" if retrieval_status else ""
    return answer + issue + status


def is_light_social_message(question: str) -> bool:
    """Detect greetings that should not trigger RAG retrieval or citations."""
    normalized = re.sub(r"[^a-zA-Z0-9\s]", " ", question.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    social_patterns = [
        r"^(hi|hello|hey|namaste|good morning|good afternoon|good evening)( sir)?$",
        r"^how are you( doing)?( sir)?$",
        r"^how r u( sir)?$",
        r"^what'?s up( sir)?$",
    ]
    return any(re.match(pattern, normalized) for pattern in social_patterns)


def social_response() -> GeneratedResponse:
    return GeneratedResponse(
        answer=(
            "I am doing well, thank you. I am AndrewAI, an educational simulation inspired by "
            "Andrew Ng's public teaching style. Ask me an AI or machine learning question, and I will "
            "try to explain it with intuition, a simple example, and practical next steps."
        ),
        sources=[],
        context_confidence="low",
        retrieval_status="Social greeting handled without retrieval.",
    )


class ResponseGenerator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.memory = MemoryManager(self.settings.sqlite_memory_db)
        self.retriever = HybridRetriever(self.settings)
        self.llm = GeminiClient(self.settings)

    def generate_response(
        self,
        user_id: str,
        user_question: str,
        conversation_history: list[dict[str, Any]] | None = None,
        response_depth: str = "standard",
    ) -> GeneratedResponse:
        question = user_question.strip()
        if not question:
            return GeneratedResponse("Please enter a question so I can help.", [], "low", "Empty input.")
        if is_light_social_message(question):
            return social_response()

        history = conversation_history or []
        memories = self.memory.get_relevant_memories(user_id, question, limit=5)
        retrieval = self.retriever.retrieve_context(question, self.settings.top_k)
        no_docs = self.retriever.indexed_count() == 0
        timeline_events: list[dict[str, Any]] = []
        timeline_rules = ""
        if self.settings.enable_timeline and is_timeline_sensitive_query(question):
            timeline_events = get_relevant_timeline_events(question, top_k=5)
            timeline_rules = get_timeline_guardrail_text()

        prompt = build_prompt(
            question=question,
            conversation_history=history[-10:],
            memories=memories,
            retrieved_chunks=retrieval.chunks,
            context_confidence=retrieval.context_confidence,
            response_depth=response_depth.lower(),
            timeline_events=timeline_events,
            timeline_rules=timeline_rules,
        )

        try:
            answer = self.llm.generate(prompt)
        except LLMError as exc:
            answer = _fallback_answer(question, retrieval.status_message, no_docs, retrieval.chunks, exc)

        candidate = self.memory.extract_memory_candidate(question, answer)
        if candidate:
            self.memory.save_memory(user_id, **candidate)

        return GeneratedResponse(
            answer=answer,
            sources=unique_sources(retrieval.chunks),
            context_confidence=retrieval.context_confidence,
            retrieval_status=retrieval.status_message,
            timeline_events=timeline_events,
        )


def generate_response(
    user_id: str,
    user_question: str,
    conversation_history: list[dict[str, Any]] | None = None,
    response_depth: str = "standard",
) -> GeneratedResponse:
    return ResponseGenerator().generate_response(user_id, user_question, conversation_history, response_depth)
