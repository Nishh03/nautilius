# Project 1 - Churn Predictor

October 2026. Telecom churn, tabular, end to end.

The point is not the model - a gradient boosting baseline solves this. The point
is everything around it: clean [[Feature Engineering]], honest
[[Model Evaluation Metrics]] on an imbalanced target, and a deployed endpoint.

Plan:
- EDA, then a logistic regression baseline before anything fancier
- Boosted trees, compared honestly against that baseline
- Optimise for recall - a missed churner costs more than a wasted retention offer
- Serve with [[Serving a Model with FastAPI]], containerise, deploy free

Writeup must include what did *not* work. That is the part that reads as real.

Related: [[Month 2 - Classical ML]], [[Portfolio Strategy]]
