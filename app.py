"""Streamlit demo for the digital twin."""

from __future__ import annotations

import hashlib
import json

import streamlit as st
import streamlit.components.v1 as components

from src.config import get_settings
from src.llm import GeminiClient, LLMError
from src.memory_manager import MemoryManager
from src.response_generator import ResponseGenerator


st.set_page_config(page_title="Digital Twin", page_icon="AI", layout="wide")

settings = get_settings()


@st.cache_resource
def get_generator() -> ResponseGenerator:
    return ResponseGenerator(settings)


def get_voice_generator() -> ResponseGenerator:
    """Return a generator instance that definitely has the latest voice-capable LLM."""
    cached_generator = get_generator()
    if hasattr(cached_generator.llm, "transcribe_audio"):
        return cached_generator
    get_generator.clear()
    return get_generator()


def transcribe_voice_audio(audio_bytes: bytes, mime_type: str) -> str:
    """Transcribe audio, with a direct Gemini fallback for stale Streamlit caches."""
    voice_generator = get_voice_generator()
    if hasattr(voice_generator.llm, "transcribe_audio"):
        return voice_generator.llm.transcribe_audio(audio_bytes, mime_type)
    return GeminiClient(settings).transcribe_audio(audio_bytes, mime_type)


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_sources(sources: list[dict], context_confidence: str = "") -> None:
    st.caption("Hybrid retrieval combines ChromaDB semantic search with BM25 keyword search.")
    if context_confidence:
        st.markdown(f"**Context confidence:** {context_confidence.title()}")
    if not sources:
        st.write("No retrieved sources for this answer.")
        return

    for source in sources:
        page = source.get("page") or "N/A"
        url = source.get("url") or "No URL"
        method = source.get("retrieval_method", "retrieval")
        vector_score = float(source.get("vector_score") or 0)
        bm25_score = float(source.get("bm25_score") or 0)
        score_parts = [f"final {float(source.get('score', 0)):.2f}"]
        if vector_score:
            score_parts.append(f"vector {vector_score:.2f}")
        if bm25_score:
            score_parts.append(f"BM25 {bm25_score:.2f}")
        st.markdown(
            f"- **{source.get('source_title', 'Untitled source')}** "
            f"(page {page}, {method}, {', '.join(score_parts)})  \n"
            f"  {url}"
        )


def render_timeline(events: list[dict] | None) -> None:
    if not events:
        return
    with st.expander("Timeline context"):
        for event in events:
            st.markdown(
                f"- **{event.get('year')}** - {event.get('event')} "
                f"({event.get('category')}, {event.get('confidence')})"
            )


def render_personalized_context(memories: list[dict] | None) -> None:
    with st.expander("Personalized teaching context"):
        if not memories:
            st.write("No relevant long-term memory was used for this answer.")
            return
        st.caption("These saved preferences or project notes helped shape the explanation.")
        for memory in memories:
            st.markdown(
                f"- **{memory.get('memory_type', 'memory').replace('_', ' ').title()}**: "
                f"{memory.get('content', '')}"
            )


def render_voice_player(text: str, autoplay: bool = False) -> None:
    """Render browser speech controls for an assistant answer."""
    payload = json.dumps(text)
    autoplay_js = "startSpeaking();" if autoplay else ""
    components.html(
        f"""
        <div style="display:flex; gap:8px; align-items:center; margin: 6px 0 2px;">
          <button id="speak-answer" type="button" style="padding:6px 10px; border:1px solid #444; border-radius:6px; background:#111827; color:white; cursor:pointer;">
            Speak answer
          </button>
          <button id="stop-answer" type="button" style="padding:6px 10px; border:1px solid #999; border-radius:6px; background:white; color:#111827; cursor:pointer;">
            Stop
          </button>
          <span id="voice-status" style="font: 13px sans-serif; color:#6b7280;">Uses your browser's text-to-speech voice.</span>
        </div>
        <script>
          (() => {{
            const answerText = {payload};
            const speakButton = document.getElementById("speak-answer");
            const stopButton = document.getElementById("stop-answer");
            const status = document.getElementById("voice-status");
            let chunks = [];
            let chunkIndex = 0;

            function setStatus(message) {{
              status.textContent = message;
            }}

            function splitForSpeech(text) {{
              const normalized = text.replace(/\\s+/g, " ").trim();
              if (!normalized) return [];
              const sentences = normalized.match(/[^.!?]+[.!?]*/g) || [normalized];
              const output = [];
              let current = "";
              for (const sentence of sentences) {{
                const next = `${{current}} ${{sentence}}`.trim();
                if (next.length > 180 && current) {{
                  output.push(current);
                  current = sentence.trim();
                }} else {{
                  current = next;
                }}
              }}
              if (current) output.push(current);
              return output.flatMap((part) => {{
                if (part.length <= 220) return [part];
                const pieces = [];
                for (let i = 0; i < part.length; i += 180) {{
                  pieces.push(part.slice(i, i + 180));
                }}
                return pieces;
              }});
            }}

            function chooseVoice(utterance) {{
              const voices = window.speechSynthesis.getVoices();
              const preferred = voices.find((voice) =>
                voice.lang && voice.lang.toLowerCase().startsWith("en")
              );
              if (preferred) utterance.voice = preferred;
            }}

            function speakNextChunk() {{
              if (chunkIndex >= chunks.length) {{
                setStatus("Finished speaking.");
                return;
              }}

              const utterance = new SpeechSynthesisUtterance(chunks[chunkIndex]);
              utterance.lang = "en-US";
              utterance.rate = 0.95;
              utterance.pitch = 1.0;
              chooseVoice(utterance);
              utterance.onend = () => {{
                chunkIndex += 1;
                speakNextChunk();
              }};
              utterance.onerror = (event) => {{
                setStatus(`Speech could not play: ${{event.error || "browser blocked it"}}.`);
              }};
              window.speechSynthesis.speak(utterance);
            }}

            function startSpeaking() {{
              if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {{
                alert("Text-to-speech is not supported in this browser.");
                setStatus("Text-to-speech is not supported in this browser.");
                return;
              }}

              window.speechSynthesis.cancel();
              chunks = splitForSpeech(answerText);
              chunkIndex = 0;
              if (!chunks.length) {{
                setStatus("There is no answer text to speak.");
                return;
              }}
              setStatus("Speaking...");
              window.setTimeout(speakNextChunk, 120);
            }}

            function stopSpeaking() {{
              if ("speechSynthesis" in window) {{
                window.speechSynthesis.cancel();
              }}
              setStatus("Stopped.");
            }}

            if ("speechSynthesis" in window) {{
              window.speechSynthesis.getVoices();
              window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
            }}

            speakButton.addEventListener("click", startSpeaking);
            stopButton.addEventListener("click", stopSpeaking);
            {autoplay_js}
          }})();
        </script>
        """,
        height=56,
    )


init_session()

with st.sidebar:
    st.header("Session")
    user_id = st.text_input("User ID", value="default_user")
    response_depth = st.selectbox("Response depth", ["Simple", "Standard", "Deep"], index=1)
    compare_modes = st.toggle("Compare response modes", value=False)
    show_sources = st.toggle("Show sources", value=True)
    voice_enabled = st.toggle("Voice interaction", value=False)
    auto_read_answers = st.toggle("Auto-read latest answer", value=False, disabled=not voice_enabled)
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
    st.subheader("Personalized teaching")
    teaching_preference = st.selectbox(
        "Preferred style",
        [
            "Examples before equations",
            "Beginner-friendly intuition",
            "Project-focused advice",
            "More technical depth",
            "Short revision notes",
        ],
    )
    if st.button("Save teaching style", use_container_width=True):
        MemoryManager(settings.sqlite_memory_db).save_memory(
            user_id=user_id,
            memory_type="preference",
            content=f"User prefers {teaching_preference.lower()}.",
            importance=5,
        )
        st.success("Teaching preference saved.")

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


st.title("Digital Twin Inspired by Andrew Ng")
if voice_enabled:
    st.subheader("Voice question")
    st.caption("Record a question, let Gemini transcribe it, then submit the transcript.")
    if st.session_state.pop("clear_voice_transcript_after_submit", False):
        st.session_state.voice_transcript_edit = ""

    voice_audio = st.audio_input("Speak to the digital twin")
    if voice_audio is not None:
        audio_bytes = voice_audio.getvalue()
        audio_hash = hashlib.sha256(audio_bytes).hexdigest()
        if st.session_state.get("last_voice_audio_hash") != audio_hash:
            with st.spinner("Transcribing voice question with Gemini..."):
                try:
                    transcript = transcribe_voice_audio(
                        audio_bytes,
                        getattr(voice_audio, "type", "audio/wav") or "audio/wav",
                    )
                    st.session_state.last_voice_audio_hash = audio_hash
                    st.session_state.voice_transcript_edit = transcript
                except LLMError as exc:
                    st.error(f"Could not transcribe voice input: {exc}")

    if st.session_state.get("voice_transcript_edit"):
        st.text_area("Voice transcript", key="voice_transcript_edit", height=80)
        if st.button("Ask using voice transcript", type="primary"):
            cleaned_transcript = st.session_state.voice_transcript_edit.strip()
            if cleaned_transcript:
                st.session_state.pending_question = cleaned_transcript
                st.session_state.clear_voice_transcript_after_submit = True
                st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and voice_enabled:
            render_voice_player(message["content"])
        if message["role"] == "assistant" and show_sources and message.get("sources"):
            with st.expander("Retrieved sources"):
                render_sources(message["sources"], message.get("context_confidence", ""))
        if message["role"] == "assistant" and message.get("used_memories") is not None:
            render_personalized_context(message.get("used_memories"))
        if message["role"] == "assistant" and message.get("timeline_events"):
            render_timeline(message.get("timeline_events"))

question = st.session_state.pop("pending_question", None) if "pending_question" in st.session_state else None
question = question or st.chat_input("Ask an AI/ML learning question...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking step by step..."):
            if compare_modes:
                comparison = generator.generate_comparison_response(
                    user_id=user_id,
                    user_question=question,
                    conversation_history=st.session_state.messages[:-1],
                    response_depths=["simple", "standard", "deep"],
                )
                selected_result = comparison.get(response_depth.lower()) or comparison["standard"]
            else:
                selected_result = generator.generate_response(
                    user_id=user_id,
                    user_question=question,
                    conversation_history=st.session_state.messages[:-1],
                    response_depth=response_depth.lower(),
                )
                comparison = {response_depth.lower(): selected_result}

        if compare_modes:
            tabs = st.tabs(["Simple", "Standard", "Deep"])
            for tab, depth in zip(tabs, ["simple", "standard", "deep"]):
                result = comparison[depth]
                with tab:
                    st.markdown(result.answer)
                    if voice_enabled:
                        render_voice_player(result.answer)
                    if result.retrieval_status:
                        st.caption(result.retrieval_status)
                    if show_sources:
                        with st.expander("Retrieved sources"):
                            render_sources(result.sources, result.context_confidence)
                    render_personalized_context(result.used_memories)
                    render_timeline(result.timeline_events)
        else:
            result = selected_result
            st.markdown(result.answer)
            if voice_enabled:
                render_voice_player(result.answer, autoplay=auto_read_answers)
            if result.retrieval_status:
                st.caption(result.retrieval_status)
            if show_sources:
                with st.expander("Retrieved sources"):
                    render_sources(result.sources, result.context_confidence)
            render_personalized_context(result.used_memories)
            render_timeline(result.timeline_events)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": selected_result.answer,
            "sources": selected_result.sources,
            "context_confidence": selected_result.context_confidence,
            "timeline_events": selected_result.timeline_events or [],
            "used_memories": selected_result.used_memories or [],
        }
    )
