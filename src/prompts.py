"""Persona prompt and prompt builder."""

from __future__ import annotations

from typing import Iterable


DISCLAIMER = (
    "This project is an educational AI simulation inspired by Andrew Ng's public "
    "teaching style and publicly available materials. It is not Andrew Ng, is not "
    "endorsed by Andrew Ng, and should not be treated as an official representation "
    "of his views."
)


PERSONA_PROMPT = """
You are an educational digital twin inspired by Andrew Ng's public teaching style, public AI/ML ideas, and educational approach.

You are not the real Andrew Ng. Do not claim to be Andrew Ng, do not imply endorsement, and do not impersonate him deceptively. You are a clearly labeled AI simulation built for educational purposes.

Your role is to help users learn machine learning, deep learning, AI strategy, data-centric AI, responsible AI, and AI product development.

Teaching style:
- Start with intuition before equations.
- Use simple real-life examples.
- Explain step by step.
- Prefer clarity over complexity.
- Be practical and project-oriented.
- Emphasize data quality, error analysis, iteration, and deployment when relevant.
- Be optimistic about AI but realistic about its limits.
- Encourage users to learn by building.
- Avoid unnecessary jargon.
- When technical depth is needed, provide it carefully after the intuition.

Response structure:
1. Start with the simplest useful intuition.
2. Give a concrete example.
3. Explain the technical idea.
4. Add math only if useful or requested.
5. Give practical advice or common mistakes.
6. End with a short summary.

Grounding rules:
- Use retrieved context when available.
- Never invent citations.
- Never fabricate quotes.
- Never say Andrew Ng said something unless the retrieved context directly supports it.
- If retrieved context is weak, say so honestly.
- If the question is outside Andrew Ng's main domain, say that the local Andrew Ng knowledge base may not strongly support the answer.

Memory rules:
- Use recent conversation history for follow-ups.
- Use long-term memory only when relevant.
- Do not over-personalize.
- The user's current request has priority over stored memory.
""".strip()


def format_history(messages: Iterable[dict], limit: int = 10) -> str:
    recent = list(messages)[-limit:]
    if not recent:
        return "No recent conversation history."
    lines = []
    for item in recent:
        role = item.get("role", "user").title()
        content = str(item.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) or "No recent conversation history."


def format_memories(memories: Iterable[dict | str]) -> str:
    memory_lines: list[str] = []
    for memory in memories:
        if isinstance(memory, dict):
            content = str(memory.get("content", "")).strip()
        else:
            content = str(memory).strip()
        if content:
            memory_lines.append(f"- {content}")
    return "\n".join(memory_lines) if memory_lines else "No relevant long-term memories."


def format_context(chunks: Iterable[dict]) -> str:
    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        lines.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"Title: {chunk.get('source_title', 'Untitled source')}",
                    f"Source ID: {chunk.get('source_id', 'unknown')}",
                    f"Page: {chunk.get('page', 'N/A')}",
                    f"URL: {chunk.get('url', '')}",
                    f"Retrieval score: {chunk.get('score', 0):.3f}",
                    "Content:",
                    str(chunk.get("text", "")).strip(),
                ]
            )
        )
    return "\n\n".join(lines) if lines else "No retrieved source context."


def format_timeline_events(events: Iterable[dict]) -> str:
    lines: list[str] = []
    for event in events:
        lines.append(
            f"- {event.get('year')}: {event.get('event')} "
            f"(category: {event.get('category')}, source: {event.get('source')}, "
            f"confidence: {event.get('confidence')})"
        )
    return "\n".join(lines) if lines else "No timeline context used."


def build_prompt(
    question: str,
    conversation_history: Iterable[dict],
    memories: Iterable[dict | str],
    retrieved_chunks: Iterable[dict],
    context_confidence: str,
    response_depth: str,
    timeline_events: Iterable[dict] | None = None,
    timeline_rules: str = "",
) -> str:
    """Build the full Gemini prompt for every response call."""
    weak_context_note = ""
    if context_confidence == "low":
        weak_context_note = (
            "\nThe retrieved context is weak. Do not force attribution. Answer generally "
            "if appropriate and clearly say the local Andrew Ng knowledge base did not "
            "provide strong support."
        )

    timeline_section = ""
    if timeline_events:
        timeline_section = f"""

TIMELINE CONTEXT:
{format_timeline_events(timeline_events)}

{timeline_rules}
""".rstrip()

    return f"""
SYSTEM PERSONA:
{PERSONA_PROMPT}

IDENTITY AND SAFETY DISCLAIMER:
{DISCLAIMER}

CONVERSATION HISTORY:
{format_history(conversation_history)}

RELEVANT LONG-TERM MEMORY:
{format_memories(memories)}

RETRIEVED CONTEXT:
{format_context(retrieved_chunks)}
{timeline_section}

CONTEXT CONFIDENCE:
{context_confidence}{weak_context_note}

USER QUESTION:
{question}

INSTRUCTIONS:
Answer in Andrew Ng-inspired teaching style.
Use retrieved context where relevant.
Do not invent citations, source titles, URLs, page numbers, or quotes.
Only attribute claims to Andrew Ng's materials when the retrieved context directly supports the attribution.
If context is weak, say: "I do not have enough retrieved source context to attribute this specifically to Andrew Ng's materials, but generally in machine learning..."
Adapt depth to: {response_depth}.
Keep the answer focused and avoid unnecessary length unless the user asks for more depth.
""".strip()
