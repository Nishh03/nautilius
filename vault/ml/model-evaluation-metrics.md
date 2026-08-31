# Model Evaluation Metrics

The part I hand-waved for a year and got caught on.

**Accuracy lies on imbalanced data.** A model predicting "no churn" for everyone
scores 95% on a 5% churn dataset and is worthless.

- **Precision** - of what I flagged, how much was right
- **Recall** - of what was actually there, how much did I catch
- **F1** - their harmonic mean, when you need one number
- **ROC-AUC** - ranking quality across all thresholds

Which to optimise is a business question, not a maths one. Fraud detection
wants recall, spam filtering wants precision.

Related: [[Probability and Statistics]], [[Project 1 - Churn Predictor]]
