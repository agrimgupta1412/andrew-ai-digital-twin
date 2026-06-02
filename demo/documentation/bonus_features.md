# Bonus Features

I implemented two bonus features in this project: a Memory Visualization Dashboard and Timeline Awareness.

## 1. Memory Visualization Dashboard

The Memory Dashboard shows what AndrewAI remembers about the current user.

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

## Future Work

Voice interaction is not implemented yet. It can be added later, but for this version I focused on memory and timeline because they show more system design.
