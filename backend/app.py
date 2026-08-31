"""HTTP layer - routes only, no logic. All work lives in vault/retrieve/llm.

Endpoint            Requirement
GET  /api/health    provider status for the UI header
GET  /api/stats     FR3, FR7  - note counts per domain
GET  /api/notes     FR2       - every note with title, domain, modified
GET  /api/graph     FR4       - wikilink graph + broken links
GET  /api/note/...  FR6       - read one note, so sources are clickable
POST /api/ask       FR5, FR6  - grounded answer with named sources
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
import llm
import retrieve
import vault

app = FastAPI(title="Nautilus", version="0.1.0")

# The frontend is a plain file the user may open directly, so allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    domain: str | None = None      # FR8 - restrict the answer to one domain


@app.get("/api/health")
def health():
    info = llm.health()
    info["vault"] = str(config.VAULT_PATH)
    info["vault_exists"] = config.VAULT_PATH.exists()
    return info


@app.get("/api/stats")
def stats():
    """FR3 + FR7 - the numbers the orbit and stat cards are drawn from."""
    notes = vault.load_notes()
    graph = vault.build_graph(notes)
    return {
        "total": len(notes),
        "domains": vault.domain_counts(notes),
        "links": len(graph["edges"]),
        "broken_links": len(graph["broken"]),
        "orphans": len(graph["orphans"]),
        "words": sum(len(n.body.split()) for n in notes),
    }


@app.get("/api/notes")
def notes(domain: str | None = None, limit: int = 200):
    """FR2 - the note list, newest first, optionally filtered by domain (FR8)."""
    items = vault.load_notes()
    if domain:
        items = [n for n in items if n.domain == domain]
    return {"count": len(items), "notes": [n.to_dict() for n in items[:limit]]}


@app.get("/api/graph")
def graph():
    """FR4 - link graph including broken links."""
    return vault.build_graph(vault.load_notes())


@app.get("/api/note/{slug:path}")
def note(slug: str):
    """Open a source note - makes FR6 citations verifiable in one click."""
    for n in vault.load_notes():
        if n.slug == slug:
            return n.to_dict(include_body=True)
    raise HTTPException(status_code=404, detail=f"No note '{slug}'")


@app.post("/api/ask")
def ask(req: AskRequest):
    """FR5 + FR6 - retrieve, ground, answer, cite."""
    items = vault.load_notes()
    if req.domain:
        items = [n for n in items if n.domain == req.domain]
    hits = [n for n, _ in retrieve.search(req.question, items)]
    try:
        result = llm.ask(req.question, hits)
    except llm.LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result["question"] = req.question
    return result


# Serve the frontend from the same origin so localhost:8000 just works.
FRONTEND = config.PROJECT_ROOT / "frontend"
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=config.HOST, port=config.PORT, reload=True)
