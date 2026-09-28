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

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

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

STARTED = time.time()
AUTOMATION = config.PROJECT_ROOT / "automation"
HISTORY = AUTOMATION / "history.log"
sys.path.insert(0, str(AUTOMATION))
import registry  # noqa: E402


def _last_runs() -> dict[str, dict]:
    """Last run of each agent, straight out of the audit log."""
    runs: dict[str, dict] = {}
    if not HISTORY.exists():
        return runs
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        runs[parts[2]] = {"when": f"{parts[0]} {parts[1]}",
                          "mode": parts[3], "summary": parts[4].strip()}
    return runs

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


SUBSTANTIAL = 40      # words before a topic counts as learned, not just named


@app.get("/api/path")
def learning_path():
    """The learning path: stages, topics, and what is unlocked next.

    Stages come from the roadmap month notes; the topics of a stage are the
    notes that month links to. A topic is DONE when its note exists and has
    real content, NEXT when it sits in the earliest stage that is not finished,
    and LOCKED when a stage ahead of that still has work in it.

    The plan grades itself against the vault, so there is no second checklist
    to keep in sync - writing the note is what completes the topic.
    """
    notes = vault.load_notes()
    by_title = {n.title.lower(): n for n in notes}

    months = sorted(
        (n for n in notes
         if n.domain == "roadmap" and n.title.lower().startswith("month")),
        key=lambda n: n.title,
    )

    stages = []
    for m in months:
        topics = []
        for target in m.links:
            t = target.strip()
            if t.lower().startswith("month") or t.lower() == "six month plan":
                continue          # navigation between stages, not a topic
            hit = by_title.get(t.lower())
            done = bool(hit and len(hit.body.split()) >= SUBSTANTIAL)
            topics.append({
                "title": t,
                "slug": hit.slug if hit else None,
                "domain": hit.domain if hit else None,
                "words": len(hit.body.split()) if hit else 0,
                "links": [l for l in (hit.links if hit else [])],
                "done": done,
            })
        # de-duplicate while preserving the order the plan lists them in
        seen, unique = set(), []
        for t in topics:
            if t["title"].lower() in seen:
                continue
            seen.add(t["title"].lower())
            unique.append(t)
        stages.append({
            "stage": m.title,
            "slug": m.slug,
            "topics": unique,
            "done": sum(t["done"] for t in unique),
            "total": len(unique),
        })

    # The current stage is the first one not yet finished. Everything before it
    # is cleared, everything after it is locked.
    current = next((i for i, s in enumerate(stages) if s["done"] < s["total"]),
                   len(stages) - 1 if stages else 0)
    for i, st in enumerate(stages):
        st["state"] = "cleared" if i < current else ("current" if i == current else "locked")
        for t in st["topics"]:
            t["state"] = ("done" if t["done"]
                          else "next" if i == current
                          else "locked")

    total = sum(s["total"] for s in stages)
    done = sum(s["done"] for s in stages)
    up_next = [t["title"] for s in stages if s["state"] == "current"
               for t in s["topics"] if t["state"] == "next"]
    return {
        "stages": stages,
        "current": current,
        "done": done,
        "total": total,
        "pct": round(100 * done / total) if total else 0,
        "up_next": up_next,
    }


@app.get("/api/agents")
def agents():
    """Every agent, its schedule, and when it last ran."""
    runs = _last_runs()
    return {"agents": [
        {"name": a.name, "label": a.label, "blurb": a.blurb,
         "schedule": a.schedule, "network": a.network, "writes": a.writes,
         "slow": a.slow, "last": runs.get(a.name)}
        for a in registry.AGENTS
    ]}


@app.post("/api/agents/{name}/run")
def run_agent(name: str):
    """Dry-run one agent and return what it printed.

    Deliberately dry-run only. This endpoint executes a script, so it takes no
    arguments from the caller beyond a name checked against the registry - the
    command is built entirely from values this process already trusts. Writing
    to the vault stays a deliberate act at a terminal, not something a web
    request can trigger.
    """
    if not registry.exists(name):
        raise HTTPException(status_code=404, detail=f"No agent '{name}'")
    script = AUTOMATION / f"{name}.py"
    if not script.exists():
        raise HTTPException(status_code=501, detail=f"{name}.py is not built yet")

    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],          # no --apply, ever, from here
            capture_output=True, text=True, timeout=150,
            cwd=str(config.PROJECT_ROOT),
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"{name} was still running after 150s. Free-tier rate limits "
                   f"can make this slow - run it in a terminal to watch it.",
        )
    out = (proc.stdout or "") + (proc.stderr or "")
    return {"agent": name, "ok": proc.returncode == 0,
            "seconds": round(time.time() - started, 1),
            "output": out.strip()[-6000:]}


@app.get("/api/system")
def system():
    """Live system state for the status rail.

    Every row the dashboard shows is read from somewhere real - the running
    process, the vault on disk, or the automation audit log. Nothing here is
    a placeholder, which is the whole point of showing it.
    """
    notes = vault.load_notes()
    graph = vault.build_graph(notes)
    info = llm.health()

    # Last run of each scheduled task, straight out of the audit log.
    tasks: dict[str, dict] = {}
    if HISTORY.exists():
        for line in HISTORY.read_text(encoding="utf-8").splitlines():
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            stamp, _, task, mode, summary = parts[0], parts[1], parts[2], parts[3], parts[4]
            tasks[task] = {"when": f"{stamp} {parts[1]}", "mode": mode,
                           "summary": summary.strip()}

    up = int(time.time() - STARTED)
    return {
        "provider": info["provider"],
        "model": info["model"],
        "ready": info.get("ready", False),
        "detail": info.get("detail", ""),
        "vault": config.VAULT_PATH.name,
        "vault_path": str(config.VAULT_PATH),
        "notes": len(notes),
        "domains": len({n.domain for n in notes}),
        "edges": len(graph["edges"]),
        "broken": len(graph["broken"]),
        "orphans": len(graph["orphans"]),
        "retrieval": f"keyword · top {config.TOP_K}",
        "tasks": tasks,
        "uptime": f"{up // 3600:02d}:{up % 3600 // 60:02d}:{up % 60:02d}",
        "now": datetime.now(timezone.utc).strftime("%H:%M:%S"),
    }


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


CONCEPT_PROMPT = """Below is one note from a personal knowledge vault.

--- NOTE "{title}" ---
{body}

Break this note into the ideas it actually contains, and how they relate, so it
can be drawn as a diagram.

Reply with ONLY a JSON object:

{{"summary": "one sentence saying what this note is really about",
  "nodes": [{{"id": "n1", "label": "short phrase, 1-4 words", "kind": "core|idea|cost|benefit"}}],
  "edges": [{{"from": "n1", "to": "n2", "label": "2-4 words saying how they relate"}}],
  "takeaway": "the one thing to remember from this note"}}

Rules:
- Between 3 and 7 nodes. Exactly one node has kind "core": the central idea.
- Every edge must connect two ids that exist in nodes.
- Labels come from the note's own vocabulary. Invent nothing.
- No prose, no code fence, only the JSON object."""


@app.get("/api/map/{slug:path}")
def note_map(slug: str):
    """A concept map of one note, for the diagram on its page.

    The model only reorganises what the note already says into nodes and
    edges - it is not asked to add knowledge. Anything it returns that does
    not hold together (an edge pointing at a node that does not exist, a
    missing core) is dropped rather than drawn, because a diagram that
    invents relationships is worse than no diagram.
    """
    note = next((n for n in vault.load_notes() if n.slug == slug), None)
    if not note:
        raise HTTPException(status_code=404, detail=f"No note '{slug}'")
    if len(note.body.split()) < 20:
        return {"ok": False, "reason": "This note is too short to diagram."}

    prompt = CONCEPT_PROMPT.format(title=note.title, body=note.body[:3000])
    try:
        raw = llm.complete(prompt)
    except llm.LLMError as exc:
        return {"ok": False, "reason": str(exc)[:160]}

    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?|```$", "", raw, flags=re.M).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {"ok": False, "reason": "The model did not return a usable map."}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"ok": False, "reason": "The model did not return a usable map."}

    nodes = [n for n in (data.get("nodes") or [])
             if isinstance(n, dict) and n.get("id") and n.get("label")][:7]
    if len(nodes) < 2:
        return {"ok": False, "reason": "Not enough distinct ideas to draw."}

    ids = {n["id"] for n in nodes}
    edges = [e for e in (data.get("edges") or [])
             if isinstance(e, dict) and e.get("from") in ids and e.get("to") in ids
             and e.get("from") != e.get("to")]

    # Exactly one core, so the layout always has a centre to build around.
    if not any(n.get("kind") == "core" for n in nodes):
        nodes[0]["kind"] = "core"
    seen_core = False
    for n in nodes:
        if n.get("kind") == "core":
            if seen_core:
                n["kind"] = "idea"
            seen_core = True
        elif n.get("kind") not in {"idea", "cost", "benefit"}:
            n["kind"] = "idea"

    return {"ok": True, "title": note.title,
            "summary": str(data.get("summary", ""))[:400],
            "takeaway": str(data.get("takeaway", ""))[:400],
            "nodes": nodes, "edges": edges}


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
