# Sequence Models and RNNs

RNNs process a sequence one step at a time, carrying a hidden state forward.
LSTMs and GRUs add gates so the state survives longer.

Two fatal limitations, both fixed by attention:
- **Sequential** - step t needs step t-1, so training cannot parallelise
- **Forgetful** - information from far back degrades through the chain

I am learning these mostly as background. Nothing new gets built with RNNs, but
knowing exactly what they could not do is what makes
[[Transformers Explained]] land.

Related: [[Month 3 - Deep Learning]]
