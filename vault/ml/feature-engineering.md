# Feature Engineering

Where the actual gains live on tabular problems. A better feature beats a better
model more often than the reverse.

- Encoding categoricals: one-hot for low cardinality, target encoding for high
- Scaling - required for distance and gradient methods, irrelevant for trees
- Dates become day of week, month, is_weekend, days_since
- Ratios and differences between existing columns
- Treating missingness as a *signal*, not just something to fill

**Leakage is the deadly one.** A feature computed using information from the
future, or from the target, produces a brilliant model that fails instantly in
production.

Related: [[Project 1 - Churn Predictor]], [[Month 2 - Classical ML]]
