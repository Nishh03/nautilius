# Decision Trees and Ensembles

A single tree splits the data on one feature at a time. Easy to read, easy to
overfit - a deep enough tree memorises the training set.

**Random forests** average many trees trained on random subsets, cancelling out
individual overfitting. **Gradient boosting** (XGBoost, LightGBM) instead trains
each tree to fix the previous one's mistakes.

On tabular data, boosted trees still beat neural networks most of the time.
This surprised me and is worth remembering before reaching for deep learning.

Related: [[Overfitting and Regularisation]], [[Project 1 - Churn Predictor]]
