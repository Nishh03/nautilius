# Neural Network Basics

A neuron is a weighted sum plus a bias, passed through a non-linear function.
That is the entire unit.

Stacked in layers, these approximate almost any function - but only because of
the non-linearity. Without an activation function, ten stacked layers collapse
mathematically into one, and the network learns nothing a line could not.

**ReLU** is the default activation: max(0, x). Cheap, and it avoids the
vanishing gradients that sigmoid suffers from in deep stacks.

Related: [[Backpropagation]], [[Linear Algebra for ML]], [[Month 3 - Deep Learning]]
