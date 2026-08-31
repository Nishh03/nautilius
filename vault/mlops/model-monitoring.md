# Model Monitoring

A deployed model degrades silently. It does not throw an exception, it just
gets slowly wronger.

What to watch:
- **Data drift** - the inputs stop resembling the training data
- **Concept drift** - the relationship itself changes. COVID broke essentially
  every demand forecast for this reason.
- **Prediction distribution** - a sudden shift in output mix is an early alarm
- Latency and error rates, like any service

Ground truth usually arrives late, so proxy signals do the work in the meantime.

Related: [[Serving a Model with FastAPI]], [[Feature Engineering]]
