from src.config import _load_google_api_keys
from src.llm import GeminiClient, LLMError


def test_numbered_google_api_keys_are_loaded_in_order(monkeypatch):
    for name in ["GOOGLE_API_KEY", "GOOGLE_API_KEYS"]:
        monkeypatch.delenv(name, raising=False)
    for index in range(1, 5):
        monkeypatch.delenv(f"GOOGLE_API_KEY_{index}", raising=False)

    monkeypatch.setenv("GOOGLE_API_KEY_1", "key-1")
    monkeypatch.setenv("GOOGLE_API_KEY_2", "key-2")
    monkeypatch.setenv("GOOGLE_API_KEY_4", "key-4")

    assert _load_google_api_keys() == ["key-1", "key-2", "key-4"]


def test_gemini_client_tries_next_key_after_quota_error():
    class FakeSettings:
        google_api_key = "key-1"
        google_api_keys = ["key-1", "key-2"]
        gemini_model = "gemini-2.5-flash"
        request_timeout_seconds = 1

    client = GeminiClient(FakeSettings())
    used_keys = []

    def fake_request(api_key, parts):
        used_keys.append(api_key)
        if api_key == "key-1":
            raise LLMError("429 quota exceeded")
        return "answer from backup key"

    client._request_with_key = fake_request

    assert client.generate("hello") == "answer from backup key"
    assert used_keys == ["key-1", "key-2"]
