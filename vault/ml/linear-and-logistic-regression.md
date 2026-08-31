# Linear and Logistic Regression

The base case. If a fancier model cannot beat regression, it is not earning its
complexity.

**Linear regression** fits a straight line by minimising squared error.
**Logistic regression** wraps that line in a sigmoid to output a probability,
and is a classifier despite the name.

Both are trained with gradient descent, which makes them the cleanest possible
demonstration of [[Calculus and Gradients]].

Why they still matter: they are interpretable. A coefficient tells you the
direction and size of an effect, which a boosted forest will not.

Related: [[Model Evaluation Metrics]], [[Month 2 - Classical ML]]
