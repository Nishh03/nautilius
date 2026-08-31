# What an LLM Actually Does

It predicts the next token. That is the whole objective.

Everything else - reasoning, translation, code - is an emergent consequence of
doing that extremely well over a large enough corpus. Which is either
underwhelming or astonishing depending on the day.

Things this framing explains:
- Why it hallucinates: a plausible continuation is not a true one, and nothing
  in the objective rewards truth. See [[LLM Hallucination]].
- Why prompt wording matters so much: different context, different distribution
- Why it cannot know anything after its training cutoff, which is the entire
  argument for [[Retrieval-Augmented Generation]]

Related: [[Transformers Explained]], [[Month 4 - LLMs and RAG]]
