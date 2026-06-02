"""Streamlit page for inspecting and editing long-term memories."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import get_settings
from src.memory_manager import MemoryManager


st.set_page_config(page_title="AndrewAI Memory Dashboard", page_icon="Memory", layout="wide")

settings = get_settings()
st.title("AndrewAI Memory Dashboard")
st.info(
    "AndrewAI stores only useful learning preferences and project context. "
    "You can inspect, edit, or delete any memory here."
)

if not settings.enable_memory_dashboard:
    st.warning("Memory dashboard is disabled by configuration.")
    st.stop()

manager = MemoryManager(settings.sqlite_memory_db)
user_id = st.text_input("User ID", value="default_user")
search_query = st.text_input("Search memories", value="")

memories = manager.search_memories(user_id, search_query) if search_query else manager.get_all_memories(user_id)

if st.button("Clear all memories", type="secondary"):
    manager.clear_user_memory(user_id)
    st.success("All long-term memories for this user were cleared.")
    st.rerun()

if not memories:
    st.write("No long-term memories stored yet.")
else:
    df = pd.DataFrame(memories)
    st.dataframe(
        df[["id", "memory_type", "content", "importance", "created_at", "updated_at"]],
        use_container_width=True,
        hide_index=True,
    )

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Memory count by type")
        st.bar_chart(df["memory_type"].value_counts())
    with chart_col2:
        st.subheader("Importance distribution")
        st.bar_chart(df["importance"].value_counts().sort_index())

    st.subheader("Edit Memories")
    for memory in memories:
        memory_id = int(memory["id"])
        with st.expander(f"Memory {memory_id}: {memory['memory_type']}"):
            new_content = st.text_area(
                "Content",
                value=memory["content"],
                key=f"content_{memory_id}",
            )
            new_importance = st.number_input(
                "Importance",
                min_value=1,
                max_value=5,
                value=int(memory.get("importance", 3)),
                step=1,
                key=f"importance_{memory_id}",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save updated memory", key=f"save_{memory_id}"):
                    if manager.update_memory(memory_id, user_id, new_content, int(new_importance)):
                        st.success("Memory updated.")
                        st.rerun()
                    else:
                        st.error("Could not update memory.")
            with col2:
                if st.button("Delete memory", key=f"delete_{memory_id}"):
                    if manager.delete_memory(memory_id, user_id):
                        st.success("Memory deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete memory.")
