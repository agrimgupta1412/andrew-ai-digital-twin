from src.response_generator import is_light_social_message, social_response


def test_social_greeting_does_not_need_retrieval():
    assert is_light_social_message("how are you sir?")
    response = social_response()
    assert response.sources == []
    assert "AndrewAI" in response.answer
    assert response.retrieval_status == "Social greeting handled without retrieval."
