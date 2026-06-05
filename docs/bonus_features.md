# Bonus Features

I implemented several bonus features in this project: a Memory Visualization Dashboard, Timeline Awareness, Compare Modes, Personalized Teaching Controls, Hybrid Retrieval Details, Voice Interaction, and multiple Gemini API key rotation.

## 1. Memory Visualization Dashboard

The Memory Dashboard shows what the digital twin remembers about the current user.

From the dashboard, the user can:

- View stored memories.
- Search memories.
- Edit memory text.
- Change importance score.
- Delete one memory.
- Clear all memories for the selected user ID.

I added this because long-term memory can feel confusing if it is hidden. The dashboard makes it easier to understand what the chatbot has saved and also gives the user control over it.

For example, if the user says:

> I prefer examples before equations.

Then this can be saved as a long-term memory. Later, the Memory Dashboard can show that preference.

## 2. Timeline Awareness

Timeline awareness helps the chatbot answer time-based questions more carefully.

The timeline is stored in:

```text
data/timeline/andrew_ng_timeline.json
```

The app checks for questions involving years, career history, organizations, ChatGPT, generative AI, or words like "before", "after", and "at that time".

If the question is timeline-sensitive, the app adds relevant timeline events to the prompt. This helps prevent answers that accidentally mix up time periods.

Example:

> What would Andrew Ng have said about ChatGPT in 2012?

The chatbot should not act like ChatGPT existed in 2012. Instead, it should explain that the local timeline does not support that claim, and then connect the answer to what was happening around that time.

## 3. Compare Modes

Compare Modes lets the user view Simple, Standard, and Deep answers side by side.

This is useful because different learners need different levels of detail. A beginner may want the Simple answer, while someone preparing for an exam or project may prefer the Deep answer.

The comparison uses the same user question, retrieved source context, timeline context, and relevant long-term memory for all three answer depths. This makes the comparison fair because only the explanation depth changes.

## 4. Personalized Teaching Controls

The sidebar includes quick controls for saving a preferred teaching style, such as:

- Examples before equations.
- Beginner-friendly intuition.
- Project-focused advice.
- More technical depth.
- Short revision notes.

These preferences are stored in long-term memory. When they are relevant to a future question, the chatbot includes them in the prompt and shows the personalization context below the answer.

## 5. Hybrid Retrieval Details

The project already uses hybrid retrieval internally, combining ChromaDB vector search and BM25 keyword search.

I made this more visible in the app by showing retrieval details in the source panel:

- Whether a source came from vector search, BM25, or hybrid matching.
- Final reranked score.
- Vector score when available.
- BM25 score when available.

This helps show that the answer is not just generated from the LLM. It is grounded in a retrieval pipeline that can be inspected during the demo.

## 6. Voice Interaction

Voice Interaction lets the user speak a question instead of typing it.

The app uses Streamlit's audio recorder to capture the user's voice. Gemini transcribes the audio into text, and the user can review or edit the transcript before submitting it as a normal chat question.

For hearing the twin, the app adds a Speak answer button below assistant messages. This uses the browser's built-in text-to-speech support, so it does not need a separate TTS API. Long answers are split into smaller speech chunks to make browser speech more reliable.

The app does not try to mimic Andrew Ng's exact voice. I kept the output as browser text-to-speech because I could not find a free and reliable tool that could directly provide an Andrew Ng-style voice inside the Streamlit project. Most good voice cloning options need paid APIs, GPU setup, long training time, or prepared voice datasets.

This feature makes the demo feel more like a conversational digital twin while still keeping the normal text chat available.

## 7. Multiple Gemini API Key Rotation

At first, the chatbot used only one Gemini API key. When that key reached the free-tier quota, the chatbot could not generate answers or transcribe voice input.

To make testing more reliable, I added support for four keys:

```env
GOOGLE_API_KEY_1=...
GOOGLE_API_KEY_2=...
GOOGLE_API_KEY_3=...
GOOGLE_API_KEY_4=...
```

If one key hits quota, rate limit, timeout, or temporary Gemini availability issues, the app automatically tries the next configured key. This failover is used for normal answers, voice transcription, and embedding calls.

## Future Work

Future improvements can include better voice selection, automatic silence detection, and a fully hands-free conversation mode.
