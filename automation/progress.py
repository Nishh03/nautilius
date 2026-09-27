"""Progress agent - how far through the plan the vault actually is.

    python automation/progress.py            # print the report
    python automation/progress.py --apply    # same, and keep the snapshot

Two different measurements, because they answer different questions:

  * **Roadmap coverage** - each month note in the plan links to the topics that
    month is meant to cover. A topic counts as done when a note with that title
    exists and has real content in it. So the plan grades itself against the
    vault, with no separate checklist to keep in sync.

  * **Growth** - a dated snapshot of the vault's size, appended to
    progress.jsonl. One line a day, so the trend can be charted later.

This agent never writes to the vault. It only reads notes and appends to its
own log, which is why it is marked read-only in the registry.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import common

SNAPSHOTS = common.Path(__file__).resolve().parent / "progress.jsonl"
ROADMAP_DOMAIN = "roadmap"
SUBSTANTIAL = 40          # words before a note counts as written rather than stubbed


def roadmap_coverage(notes: list) -> list[dict]:
    """Grade each month of the plan against the notes that actually exist."""
    by_title = {n.title.lower(): n for n in notes}
    months = sorted(
        (n for n in notes
         if n.domain == ROADMAP_DOMAIN and n.title.lower().startswith("month")),
        key=lambda n: n.title,
    )

    out = []
    for m in months:
        targets = [t for t in m.links if not t.lower().startswith("month")
                   and t.lower() != "six month plan"]
        done, missing = [], []
        for t in targets:
            hit = by_title.get(t.strip().lower())
            (done if hit and len(hit.body.split()) >= SUBSTANTIAL else missing).append(t)
        total = len(targets)
        out.append({
            "month": m.title,
            "total": total,
            "done": len(done),
            "pct": round(100 * len(done) / total) if total else 0,
            "missing": missing,
        })
    return out


def snapshot(notes: list, graph: dict) -> dict:
    counts = {d["domain"]: d["count"] for d in common.vault.domain_counts(notes)}
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "notes": len(notes),
        "words": sum(len(n.body.split()) for n in notes),
        "domains": len(counts),
        "links": len(graph["edges"]),
        "broken": len(graph["broken"]),
        "orphans": len(graph["orphans"]),
        "by_domain": counts,
    }


def record(snap: dict) -> str:
    """One row per day: a re-run on the same day replaces that day's row."""
    rows = []
    if SNAPSHOTS.exists():
        for line in SNAPSHOTS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("date") != snap["date"]:
                rows.append(row)
    rows.append(snap)
    rows.sort(key=lambda r: r["date"])
    SNAPSHOTS.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return f"{len(rows)} day(s) recorded"


def bar(pct: int, width: int = 22) -> str:
    filled = round(width * pct / 100)
    return "#" * filled + "." * (width - filled)


def main() -> int:
    args = common.parse_args("Progress - roadmap coverage and vault growth")
    common.banner("PROGRESS  plan vs vault", args.apply)

    notes = common.load()
    if not notes:
        return 0
    graph = common.vault.build_graph(notes)

    coverage = roadmap_coverage(notes)
    if coverage:
        common.say("  Roadmap coverage - a topic counts when its note exists "
                   f"and runs past {SUBSTANTIAL} words\n")
        for c in coverage:
            common.say(f"    {c['month']:<26} {bar(c['pct'])}  "
                       f"{c['pct']:>3}%  ({c['done']}/{c['total']})")
            if c["missing"]:
                common.say(f"      still to write: {', '.join(c['missing'][:4])}"
                           + (" …" if len(c["missing"]) > 4 else ""))
        overall = round(sum(c["done"] for c in coverage) * 100
                        / max(sum(c["total"] for c in coverage), 1))
        common.say(f"\n    overall {bar(overall)}  {overall}%")
    else:
        common.say("  No month notes found in the roadmap domain - nothing to grade.")

    snap = snapshot(notes, graph)
    common.say("")
    common.say(f"  Snapshot {snap['date']}: {snap['notes']} notes · {snap['words']} words · "
               f"{snap['links']} links · {snap['broken']} broken")

    if args.apply:
        common.say("  " + record(snap))
    else:
        common.say("  dry run - re-run with --apply to keep this snapshot")

    common.record("progress", args.apply,
                  f"{snap['notes']} notes, "
                  f"{(sum(c['done'] for c in coverage) if coverage else 0)}"
                  f"/{(sum(c['total'] for c in coverage) if coverage else 0)} topics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
