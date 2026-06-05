from src.response_generator import ResponseGenerator, is_light_social_message, social_response
from src.retriever import RetrievalResult


def test_social_greeting_does_not_need_retrieval():
    assert is_light_social_message("how are you sir?")
    response = social_response()
    assert response.sources == []
    assert "educational simulation" in response.answer
    assert response.retrieval_status == "Social greeting handled without retrieval."


def test_compare_modes_reuses_context_and_returns_each_depth():
    class FakeMemory:
        def __init__(self):
            self.saved = []

        def get_relevant_memories(self, user_id, question, limit=5):
            return [{"memory_type": "preference", "content": "User prefers examples before equations."}]

        def extract_memory_candidate(self, question, answer):
            return {"memory_type": "preference", "content": question, "importance": 4}

        def save_memory(self, user_id, **candidate):
            self.saved.append((user_id, candidate))

    class FakeRetriever:
        def __init__(self):
            self.calls = 0

        def retrieve_context(self, question, top_k):
            self.calls += 1
            return RetrievalResult(
                chunks=[
                    {
                        "chunk_id": "a",
                        "text": "Gradient descent updates parameters step by step.",
                        "source_id": "source-a",
                        "source_title": "Source A",
                        "score": 0.8,
                        "vector_score": 0.8,
                        "retrieval_method": "vector",
                    }
                ],
                context_confidence="high",
                status_message="",
            )

        def indexed_count(self):
            return 1

    class FakeLLM:
        def generate(self, prompt):
            depth = prompt.split("Adapt depth to: ", 1)[1].split(".", 1)[0]
            return f"{depth} answer"

    class FakeSettings:
        top_k = 5
        enable_timeline = False

    generator = ResponseGenerator.__new__(ResponseGenerator)
    generator.settings = FakeSettings()
    generator.memory = FakeMemory()
    generator.retriever = FakeRetriever()
    generator.llm = FakeLLM()

    responses = generator.generate_comparison_response(
        user_id="user1",
        user_question="I prefer examples before equations.",
        conversation_history=[],
        response_depths=["simple", "standard", "deep"],
    )

    assert set(responses) == {"simple", "standard", "deep"}
    assert responses["simple"].answer == "simple answer"
    assert responses["deep"].used_memories
    assert responses["standard"].sources[0]["vector_score"] == 0.8
    assert generator.retriever.calls == 1
    assert len(generator.memory.saved) == 1
