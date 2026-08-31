# Agents and Tool Use

An agent is a model in a loop with tools: decide, act, observe the result,
decide again.

The model does not run anything itself. It emits a structured request, your code
executes it, and the result goes back into context. The intelligence is in the
choosing, not the doing.

Where it breaks:
- Loops that never terminate without a step cap
- Errors compounding - a wrong step at turn 2 poisons turns 3 through 10
- Cost, since every step is a full model call

The honest lesson: most problems people reach for agents on are better solved by
one well-constructed prompt with the right context.

Related: [[Prompt Context Window]], [[Month 4 - LLMs and RAG]]
