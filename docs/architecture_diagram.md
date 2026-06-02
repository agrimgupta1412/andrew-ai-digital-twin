# AndrewAI Architecture Diagram

This is the architecture diagram for the assignment. It shows how the Streamlit app, RAG pipeline, memory, timeline feature, prompt builder, and Gemini model connect together.

```mermaid
flowchart TD
    U[User] --> UI[Streamlit Chat UI]

    subgraph UI_LAYER[App Pages]
        UI
        MD[Memory Dashboard]
        TP[Timeline Page]
    end

    subgraph MEMORY[Memory System]
        STM[Short-Term Session Memory]
        LTM[(Long-Term SQLite Memory)]
        MM[Memory Manager]
    end

    subgraph RAG[RAG Pipeline]
        RAW[Source Documents]
        MANIFEST[Sources Manifest]
        LOADER[Document Loader]
        CHUNKER[Text Chunker]
        EMBED[Embedding Client]
        CHROMA[(ChromaDB Vector Store)]
        JSONL[(Processed Chunks JSONL)]
        BM25[BM25 Keyword Retriever]
        HYBRID[Hybrid Retriever and Reranker]
    end

    subgraph TIMELINE[Timeline Awareness]
        TJSON[(Andrew Ng Timeline JSON)]
        TRET[Timeline Retriever]
        TGUARD[Timeline Guardrails]
    end

    subgraph GENERATION[Answer Generation]
        PROMPT[Prompt Builder]
        PERSONA[AndrewAI Persona and Disclaimer]
        GEMINI[Gemini 2.5 Flash]
        SOURCES[Source Formatter]
        ANSWER[Final Answer]
    end

    UI --> STM
    UI --> MM
    MM --> LTM
    LTM --> MD

    RAW --> LOADER
    MANIFEST --> LOADER
    LOADER --> CHUNKER
    CHUNKER --> JSONL
    CHUNKER --> EMBED
    EMBED --> CHROMA

    UI --> HYBRID
    CHROMA --> HYBRID
    JSONL --> BM25
    BM25 --> HYBRID

    UI --> TRET
    TJSON --> TRET
    TRET --> TGUARD
    TJSON --> TP

    STM --> PROMPT
    LTM --> PROMPT
    HYBRID --> PROMPT
    TRET --> PROMPT
    TGUARD --> PROMPT
    PERSONA --> PROMPT

    PROMPT --> GEMINI
    GEMINI --> ANSWER
    HYBRID --> SOURCES
    SOURCES --> UI
    ANSWER --> UI
    ANSWER --> MM
```

## Component Summary

- **Streamlit Chat UI**: Main page where the user asks ML questions and receives answers.
- **RAG Pipeline**: Loads documents, chunks them, stores vectors, and retrieves useful source chunks.
- **ChromaDB**: Stores embeddings for semantic search.
- **BM25**: Helps retrieve chunks using exact keywords.
- **Memory System**: Stores recent chat context and long-term user preferences.
- **Memory Dashboard**: Lets the user inspect and manage long-term memory.
- **Timeline Awareness**: Adds Andrew Ng timeline context for historical questions.
- **Prompt Builder**: Combines persona, memory, RAG context, timeline context, and user question.
- **Gemini 2.5 Flash**: Main LLM used to generate the answer.
- **Source Formatter**: Shows only the sources actually found by retrieval.

The most important design idea is that Gemini does not answer alone. It receives extra context from retrieval, memory, and timeline modules so that the response is more grounded and more useful for an ML learner.
