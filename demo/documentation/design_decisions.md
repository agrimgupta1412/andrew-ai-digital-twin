# Design Decisions

This file explains why I made some of the main choices in the project.

## Why Andrew Ng?

I chose Andrew Ng because his teaching style is very clear and recognizable. He often explains the intuition first, uses simple examples, and then connects the topic to real ML projects.

For a digital twin assignment, this was useful because I could focus on an educational teaching assistant instead of trying to copy a personality in a random way.

## Why Gemini 2.5 Flash?

The assignment required Gemini as the main LLM, so I used Gemini 2.5 Flash for answer generation.

The model name is stored in `.env`, which makes it easier to change later if needed.

## Why Streamlit?

I used Streamlit because it is good for quickly building a working ML demo. It gives chat UI, buttons, sidebars, session state, and extra pages without needing a full frontend framework.

For this project, the goal was more about the AI system design than making a complex web app, so Streamlit made sense.

## Why RAG?

A normal chatbot can answer from the model's general knowledge, but this assignment needed the digital twin to use relevant source material.

That is why I added RAG. The chatbot retrieves chunks from Andrew Ng-related documents and gives them to Gemini as context.

## Why Hybrid Retrieval?

I used both vector search and BM25 because they help in different ways.

Vector search is useful when the question has similar meaning but different wording.

BM25 is useful when the question contains exact technical words like "Adam optimizer", "L1 regularization", or "bias variance".

Combining them gives better retrieval than using only one method.

## Why SQLite For Memory?

SQLite is simple, local, and easy to inspect. It was a good fit for storing long-term memories like user preferences or project context.

I did not need a large database system for this assignment.

## Why Add A Memory Dashboard?

I added the Memory Dashboard because memory should be transparent. If the chatbot remembers something about the user, the user should be able to see it, edit it, or delete it.

This also makes the memory feature easier to demonstrate during evaluation.

## Why Add Timeline Awareness?

Timeline awareness was added to reduce historical mistakes. For example, if someone asks what Andrew Ng would have said about ChatGPT in 2012, the system should know that ChatGPT did not exist then.

I used a small JSON timeline instead of web search because it is easier to control and verify.

## Why Avoid Direct Impersonation?

The app is clearly labeled as an AI simulation inspired by Andrew Ng's public teaching style. It does not claim to be him.

This is important because the goal is educational simulation, not pretending to be a real person.

## Why No Voice Feature?

Voice interaction is listed as future work. I focused on the features that were more important for the assignment: RAG, memory, timeline awareness, source display, and documentation.
