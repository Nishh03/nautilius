# Retrieval-Augmented Generation

RAG gives a language model retrieved documents alongside the question so the
answer is grounded in real sources instead of model memory.

The core loop is: retrieve -> stuff into prompt -> generate -> cite.

Classic implementations use embeddings and a vector database, but for a personal
vault of a few hundred notes [[keyword-retrieval]] is enough and has zero
infrastructure cost.

Related: [[llm-hallucination]], [[vector-embeddings]]
