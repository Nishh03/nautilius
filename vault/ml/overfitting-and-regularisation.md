# Overfitting and Regularisation

Overfitting is memorising instead of learning: near-perfect training scores,
poor test scores.

The bias-variance framing: a too-simple model is biased and misses the pattern,
a too-complex model has high variance and chases noise.

Fixes:
- More data, if available
- **L1/L2 regularisation** - penalise large weights
- **Dropout** in neural networks, see [[Training Tricks]]
- **Early stopping** on a validation set
- **Cross-validation** to measure honestly

The discipline that matters: touch the test set once, at the end. Every peek
leaks information and inflates the result.

Related: [[Model Evaluation Metrics]], [[Decision Trees and Ensembles]]
