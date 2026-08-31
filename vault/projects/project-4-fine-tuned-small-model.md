# Project 4 - Fine-tuned Small Model

January 2027, if time allows. The stretch project.

LoRA fine-tune of a small open model on a narrow task, to prove I can train and
not only call an API.

Plan:
- Pick a task where *behaviour* matters, not facts - per [[Fine-tuning vs RAG]],
  fine-tuning for knowledge is the wrong tool
- Build the dataset carefully. Data quality dominates everything here.
- LoRA on free Colab compute
- Evaluate against the base model on held-out examples, honestly

Risk: this is the project most likely to be cut. Cutting it is fine. Shipping
three finished projects beats four half-finished ones.

Related: [[Portfolio Strategy]], [[Month 5 - MLOps]]
