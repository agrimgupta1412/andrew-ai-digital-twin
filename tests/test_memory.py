from src.memory_manager import MemoryManager


def test_db_initializes(tmp_path):
    db_path = tmp_path / "memory.db"
    MemoryManager(db_path)
    assert db_path.exists()


def test_memory_saves_retrieves_and_clears(tmp_path):
    manager = MemoryManager(tmp_path / "memory.db")
    manager.save_memory("user1", "preference", "User prefers real-life examples.", importance=4)
    memories = manager.get_relevant_memories("user1", "Can you use real-life examples?", limit=5)
    assert memories
    assert "real-life examples" in memories[0]["content"]

    manager.clear_user_memory("user1")
    assert manager.get_relevant_memories("user1", "real-life examples", limit=5) == []


def test_trivial_messages_are_not_saved(tmp_path):
    manager = MemoryManager(tmp_path / "memory.db")
    assert manager.extract_memory_candidate("hello") is None
    assert manager.extract_memory_candidate("What is gradient descent?") is None
    candidate = manager.extract_memory_candidate("I am new to machine learning.")
    assert candidate is not None
    assert candidate["memory_type"] == "learning_profile"


def test_memory_dashboard_crud_helpers_are_user_scoped(tmp_path):
    manager = MemoryManager(tmp_path / "memory.db")
    manager.save_memory("user1", "preference", "User prefers examples before equations.", importance=4)
    manager.save_memory("user2", "preference", "Other user prefers equations.", importance=5)

    user1_memories = manager.get_all_memories("user1")
    assert len(user1_memories) == 1
    assert user1_memories[0]["content"] == "User prefers examples before equations."

    memory_id = user1_memories[0]["id"]
    assert manager.search_memories("user1", "examples")
    assert manager.search_memories("user1", "equations")
    assert manager.update_memory(memory_id, "user1", "User prefers visual examples.", 5)
    assert manager.get_all_memories("user1")[0]["importance"] == 5
    assert manager.get_all_memories("user1")[0]["content"] == "User prefers visual examples."

    assert not manager.delete_memory(memory_id, "user2")
    assert manager.get_all_memories("user1")
    assert manager.delete_memory(memory_id, "user1")
    assert manager.get_all_memories("user1") == []
    assert manager.get_all_memories("user2")
