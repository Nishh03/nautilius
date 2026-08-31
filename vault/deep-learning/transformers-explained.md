# Transformers Explained

The architecture behind everything current. Budgeting a full week for this.

**Self-attention** lets every token look at every other token directly, in one
step. No sequential bottleneck, so training parallelises across a whole sequence.

Query, Key, Value: each token emits a query for what it wants, a key advertising
what it offers, and a value carrying its content. Attention weight is the dot
product of query and key - back to [[Linear Algebra for ML]].

Because attention has no notion of order, **positional encodings** add it back.

Cost: attention is quadratic in sequence length, which is why the
[[Prompt Context Window]] is finite and expensive.

To write up properly: [[Attention Is All You Need - paper notes]]

Related: [[What an LLM Actually Does]], [[Sequence Models and RNNs]]
