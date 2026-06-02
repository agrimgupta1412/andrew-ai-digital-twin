from src.prompts import PERSONA_PROMPT, build_prompt
from src.timeline.timeline_guardrails import get_timeline_guardrail_text


def test_persona_prompt_contains_identity_and_grounding_rules():
    prompt = PERSONA_PROMPT.lower()
    assert "not the real andrew ng" in prompt
    assert "do not claim to be andrew ng" in prompt
    assert "never invent citations" in prompt
    assert "use retrieved context" in prompt


def test_prompt_can_include_timeline_context_and_rules():
    prompt = build_prompt(
        question="What would Andrew Ng have said about ChatGPT in 2012?",
        conversation_history=[],
        memories=[],
        retrieved_chunks=[],
        context_confidence="low",
        response_depth="standard",
        timeline_events=[
            {
                "year": 2012,
                "event": "Andrew Ng co-founded Coursera.",
                "category": "career",
                "source": "public biography",
                "confidence": "high",
            }
        ],
        timeline_rules=get_timeline_guardrail_text(),
    ).lower()
    assert "timeline context" in prompt
    assert "do not imply andrew ng held a role" in prompt
    assert "never fabricate timeline events" in prompt
