# LLM Hallucination

Fluent, confident, wrong. The failure mode that matters most in production.

It is not a bug to be patched - it follows directly from
[[What an LLM Actually Does]]. The model optimises for plausible continuations,
and plausible is not the same as true.

Mitigations, in order of effectiveness:
1. Ground it in retrieved documents - [[Retrieval-Augmented Generation]]
2. Require citations, so a claim without a source is visibly unsupported
3. Instruct it to refuse when the context does not contain the answer
4. Lower the temperature

None of these eliminate it. Designing so a wrong answer is *visible* beats
pretending it will not happen.

Related: [[Evaluating LLM Outputs]]
