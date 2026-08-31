# Nautilus Architecture

Four backend modules, one job each.

vault.py reads the folder and builds the note list and link graph.
retrieve.py scores notes against a question.
llm.py is the only file that knows which AI provider exists.
app.py exposes four HTTP endpoints and nothing else.

No database. The vault is re-read from disk on every request, so the dashboard
can never be stale.

Related: [[orbit-visualisation]], [[non-functional-requirements]], [[keyword-retrieval]]
