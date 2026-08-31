# Prompt Context Window

The maximum number of tokens a model can read at once. Everything the model
"knows" during a request must fit inside it.

This is the real constraint on how many notes we can send with a question.
Retrieval exists because the context window is finite.

Related: [[retrieval-augmented-generation]], [[missing-note-example]]
