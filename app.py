"""Streamlit demo for AndrewAI."""

from __future__ import annotations

import streamlit as st

from src.config import get_settings
from src.memory_manager import MemoryManager
from src.prompts import DISCLAIMER
from src.response_generator import ResponseGenerator


st.set_page_config(page_title="AndrewAI", page_icon="AI", layout="wide")

settings = get_settings()


@st.cache_resource
def get_generator() -> ResponseGenerator:
    return ResponseGenerator(settings)


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


init_session()

with st.sidebar:
    st.header("Session")
    user_id = st.text_input("User ID", value="default_user")
    response_depth = st.selectbox("Response depth", ["Simple", "Standard", "Deep"], index=1)
    show_sources = st.toggle("Show sources", value=True)
    st.caption(f"Gemini timeout: {settings.request_timeout_seconds}s")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("Clear memory", use_container_width=True):
            MemoryManager(settings.sqlite_memory_db).clear_user_memory(user_id)
            st.success("Long-term memory cleared.")

    st.divider()
    generator = get_generator()
    indexed_count = generator.retriever.indexed_count()
    st.metric("Indexed chunks", indexed_count)
    if indexed_count > 0:
        st.success("RAG index ready")
    else:
        st.warning("No documents indexed")
        st.caption("Add permitted documents to data/raw/ and run python scripts/ingest_documents.py.")

    st.divider()
    st.subheader("Starter questions")
    starters = [
        "Explain gradient descent like I am new to ML.",
        "How do I know if my model has high bias or high variance?",
        "What is data-centric AI?",
        "How should I debug a machine learning model?",
        "How should I start my first AI project?",
    ]
    for starter in starters:
        if st.button(starter, use_container_width=True):
            st.session_state.pending_question = starter


st.title("AndrewAI: Digital Twin Inspired by Andrew Ng")
st.info(
    "This is an educational AI simulation inspired by Andrew Ng's public teaching style and publicly "
    "available materials. It is not Andrew Ng and is not officially affiliated with him."
)
st.caption(DISCLAIMER)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and show_sources and message.get("sources"):
            with st.expander("Retrieved sources"):
                for source in message["sources"]:
                    page = source.get("page") or "N/A"
                    url = source.get("url") or "No URL"
                    st.markdown(
                        f"- **{source.get('source_title', 'Untitled source')}** "
                        f"(page {page}, {source.get('retrieval_method', 'retrieval')}, score {source.get('score', 0):.2f})  \n"
                        f"  {url}"
                    )
        if message["role"] == "assistant" and message.get("timeline_events"):
            with st.expander("Timeline context"):
                for event in message["timeline_events"]:
                    st.markdown(
                        f"- **{event.get('year')}** - {event.get('event')} "
                        f"({event.get('category')}, {event.get('confidence')})"
                    )

question = st.session_state.pop("pending_question", None) if "pending_question" in st.session_state else None
question = question or st.chat_input("Ask an AI/ML learning question...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking step by step..."):
            result = generator.generate_response(
                user_id=user_id,
                user_question=question,
                conversation_history=st.session_state.messages[:-1],
                response_depth=response_depth.lower(),
            )
        st.markdown(result.answer)
        if result.retrieval_status:
            st.caption(result.retrieval_status)
        if show_sources:
            with st.expander("Retrieved sources"):
                if result.sources:
                    for source in result.sources:
                        page = source.get("page") or "N/A"
                        url = source.get("url") or "No URL"
                        st.markdown(
                            f"- **{source.get('source_title', 'Untitled source')}** "
                            f"(page {page}, {source.get('retrieval_method', 'retrieval')}, score {source.get('score', 0):.2f})  \n"
                            f"  {url}"
                        )
                else:
                    st.write("No retrieved sources for this answer.")
        if result.timeline_events:
            with st.expander("Timeline context"):
                for event in result.timeline_events:
                    st.markdown(
                        f"- **{event.get('year')}** - {event.get('event')} "
                        f"({event.get('category')}, {event.get('confidence')})"
                    )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": result.sources,
            "context_confidence": result.context_confidence,
            "timeline_events": result.timeline_events or [],
        }
    )
