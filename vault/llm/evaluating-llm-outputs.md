# Evaluating LLM Outputs

The skill nobody advertises and every team needs. There is no accuracy score for
"was that a good answer".

What works:
- **A fixed test set of questions** with known-good answers, run on every change
- **LLM-as-judge** - a second model scores the first. Cheap, noisy, but catches
  regressions.
- **Groundedness** - does every claim trace to a retrieved source? Automatable
  and the highest-value check for RAG.
- **Human review** on a sample. Irreplaceable, so keep the sample small enough
  to actually do.

Without this you are tuning prompts on vibes, and vibes do not survive contact
with a demo.

Related: [[LLM Hallucination]], [[Project 3 - RAG Assistant]]
