# Limitations

These are the main limitations I noticed while building and testing the project.

- AndrewAI is not the real Andrew Ng.
- It is not officially endorsed by Andrew Ng, Stanford, Coursera, or DeepLearning.AI.
- The answers depend on Gemini working properly, so API quota or network issues can affect the demo.
- The quality of RAG depends on the documents added by the user.
- Retrieval can sometimes miss a useful chunk or retrieve a weakly related chunk.
- Gemini can still make mistakes even when retrieved context is provided.
- The displayed sources should be trusted more than any citation written inside the generated answer.
- Raw copyrighted source documents should not be committed to the repository.
- Memory extraction is simple and may miss some useful preferences.
- Memory importance scoring is basic and can be improved.
- The BM25 and vector reranking logic is simple compared to a production system.
- Timeline awareness uses a small event file, so it does not cover every Andrew Ng career event.
- Voice interaction is not implemented in this version.

Overall, the system is good enough for a working assignment demo, but it is not a production-level digital twin.
