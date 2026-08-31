# Vector Embeddings and Similarity

Text mapped to a vector where similar meanings land near each other. This is
what makes semantic search possible: matching by meaning rather than by word.

**Cosine similarity** measures the angle between two vectors, ignoring
magnitude - so it compares direction, which is what carries meaning. It is the
same dot product from [[Linear Algebra for ML]], normalised.

Cost: an embedding model to encode, plus somewhere to store and search the
vectors. For a few hundred documents that overhead is not worth it, which is
why keyword retrieval is the sensible first version.

Related: [[Retrieval-Augmented Generation]], [[Prompt Context Window]]
