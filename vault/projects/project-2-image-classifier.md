# Project 2 - Image Classifier

November 2026. Transfer learning, not training from scratch.

Fine-tuning a pretrained ResNet on a small custom dataset is both what actually
works with limited data and what a real team would do.

Plan:
- Collect or find a small dataset, a few thousand images
- Freeze the backbone, retrain the head, then unfreeze the top blocks
- Augmentation to fight [[Overfitting and Regularisation]]
- Confusion matrix, not just accuracy - which classes get confused and why
- Deploy with an image upload demo

Related: [[CNNs for Vision]], [[Month 3 - Deep Learning]]
