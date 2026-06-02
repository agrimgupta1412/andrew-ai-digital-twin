from src.config import get_settings
from src.timeline.timeline_guardrails import get_timeline_guardrail_text, is_timeline_sensitive_query
from src.timeline.timeline_loader import REQUIRED_FIELDS, load_timeline
from src.timeline.timeline_retriever import get_relevant_timeline_events


def test_timeline_file_loads_sorted_events():
    events = load_timeline(get_settings().timeline_file)
    assert events
    assert [event["year"] for event in events] == sorted(event["year"] for event in events)
    assert all(REQUIRED_FIELDS.issubset(event) for event in events)


def test_timeline_sensitive_detection():
    assert is_timeline_sensitive_query("What would Andrew Ng have said about ChatGPT in 2012?")
    assert is_timeline_sensitive_query("When did Andrew Ng co-found Coursera?")
    assert not is_timeline_sensitive_query("Explain gradient descent simply.")
    assert not is_timeline_sensitive_query("How do I know if my model has high bias or high variance?")


def test_relevant_timeline_events_are_returned():
    events = get_relevant_timeline_events("What happened with Coursera in 2012?")
    assert events
    assert any(event["year"] == 2012 for event in events)
    assert any("Coursera" in event["event"] for event in events)


def test_timeline_guardrails_include_anachronism_protection():
    guardrails = get_timeline_guardrail_text().lower()
    assert "later ideas" in guardrails
    assert "earlier periods" in guardrails
    assert "never fabricate timeline events" in guardrails
