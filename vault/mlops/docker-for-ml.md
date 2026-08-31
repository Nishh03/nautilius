# Docker for ML

"Works on my machine" is the single most common reason a student project cannot
be shown to anyone.

What I need to know:
- A Dockerfile describes an image, a container is a running instance
- Order layers cheapest-changing first: install requirements before copying
  source, so a code edit does not reinstall every dependency
- Pin versions. An unpinned image is a time bomb.
- Keep images small - a slim Python base over a full one

Every project from [[Portfolio Strategy]] ships with a Dockerfile. It is the
cheapest possible signal that I have worked near production.

Related: [[Serving a Model with FastAPI]], [[Month 5 - MLOps]]
