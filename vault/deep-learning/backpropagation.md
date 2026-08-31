# Backpropagation

The algorithm that makes training possible. Two passes:

**Forward** - run the input through the network, compute the loss.
**Backward** - push the error back through, using the chain rule to work out how
much each weight contributed. Nudge every weight against its gradient.

The insight that made it click: backprop is not a learning algorithm, it is an
efficient way to compute gradients. The learning is gradient descent. Conflating
the two confused me for weeks.

Doing it by hand once on a two-layer network is worth more than three videos.

Related: [[Calculus and Gradients]], [[Neural Network Basics]]
