# Fine-tuning vs RAG

The decision I keep seeing people get backwards, including me.

**Fine-tuning teaches behaviour: format, tone, task structure.** It is the wrong
tool for facts. Baking knowledge into weights means retraining every time a
document changes, and the model still cannot cite where an answer came from.

**RAG teaches knowledge.** For domain facts, retrieval should always be the
first approach - it is cheaper, updatable, and citable.

Rule I am adopting: if the answer is "the model should know X", use RAG. If the
answer is "the model should behave like Y", fine-tune.

Related: [[Retrieval-Augmented Generation]], [[Project 4 - Fine-tuned Small Model]]
