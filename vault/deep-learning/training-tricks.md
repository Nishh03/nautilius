# Training Tricks

The gap between "it runs" and "it learns".

- **Normalise inputs** - unscaled features make the loss surface hard to descend
- **Learning rate** matters more than architecture. Too high diverges, too low
  crawls. Use a scheduler.
- **Batch normalisation** stabilises training and lets you use higher rates
- **Dropout** for regularisation, see [[Overfitting and Regularisation]]
- **Early stopping** on validation loss
- **Start by overfitting a tiny subset.** If the model cannot memorise 10
  examples, the bug is in the code, not the hyperparameters.

That last one has saved me more debugging time than anything else on this list.

Related: [[Neural Network Basics]], [[Month 3 - Deep Learning]]
