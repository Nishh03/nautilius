# Prompt Engineering Notes

Less mystical than it sounds. What consistently works:

- **Be specific about the output format.** Ambiguity gets filled unpredictably.
- **Give examples** (few-shot). Two good examples beat a paragraph of
  description.
- **Assign a role** when it usefully narrows the register.
- **Ask for reasoning before the answer**, not after - once the answer is
  generated, any reasoning after it is decoration.
- **Say what NOT to do**, explicitly. Negative constraints work.

A lesson from my own build: I told a small model to "be concise" and got
one-word answers. Instructions are followed more literally than intended, and
the smaller the model, the more literally.

Related: [[Evaluating LLM Outputs]], [[Month 4 - LLMs and RAG]]
