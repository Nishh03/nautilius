# LLM Hallucination

When a model produces fluent text that is factually wrong, usually because it
was asked about something outside its training data.

Grounding the model in retrieved documents and forcing it to name its sources
is the cheapest mitigation. If the model cannot point to a source, it should
say it does not know.

Related: [[retrieval-augmented-generation]]
