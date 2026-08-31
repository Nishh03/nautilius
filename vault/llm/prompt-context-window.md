# Prompt Context Window

The maximum tokens a model can attend to at once. Everything it "knows" during a
request must fit inside it.

This is the hard constraint behind retrieval: you cannot paste an entire vault
into a prompt, so something must choose what goes in. That chooser is the
retrieval step in [[Retrieval-Augmented Generation]].

Bigger windows have not removed the problem. Cost scales with length, and models
attend unevenly across a long context - material in the middle gets used less
reliably than material at either end.

Related: [[Transformers Explained]], [[Vector Embeddings and Similarity]]
