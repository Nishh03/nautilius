# Retrieval-Augmented Generation

Give the model the documents alongside the question so its answer is grounded in
those documents rather than in its training data.

The loop: retrieve, stuff into the prompt, generate, cite.

Why it wins for private knowledge:
- Works on data the model has never seen
- Updates instantly when a document changes - no retraining
- Sources can be cited, so [[LLM Hallucination]] becomes checkable

The retrieval step is the part that decides quality. A perfect model given the
wrong three documents produces a confident wrong answer.

Related: [[Vector Embeddings and Similarity]], [[Project 3 - RAG Assistant]]
