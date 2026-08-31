# Serving a Model with FastAPI

Turning a trained model into something another program can call.

The shape:
- Load the model once at startup, not per request
- One POST endpoint taking features, returning a prediction
- Pydantic models for request and response, which gives validation and docs free
- A /health endpoint, because every deployment platform wants one

The mistake I made first time: loading the model inside the handler. Every
request re-read the weights from disk and it was unusably slow.

Related: [[Docker for ML]], [[Model Monitoring]]
