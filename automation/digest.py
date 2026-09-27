"""FR10 - weekly digest: write a summary note of the week into the vault.

    python automation/digest.py            # dry run - prints the digest
    python automation/digest.py --apply    # write it into the vault

Intended to run every Monday. The digest is a normal markdown note with real
[[wikilinks]], so it shows up in the dashboard and the link graph like anything
else the user wrote by hand.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import common

DIGEST_DOMAIN = "digests"
DAYS = 7
NOTE_CHARS = 900       # per note sent to the model
CHUNK_CHARS = 9000     # per request; sized for a free tier's per-minute cap

PROMPT = """Below are the notes a person added or edited in the last {days} days.

{notes}

Write a short weekly digest of this work. Use exactly this structure:

## What you worked on
Two or three sentences describing the week's themes. Refer to notes by their
exact titles wrapped in double square brackets, like [[Note Title]].

## Threads to pick up
Two or three bullet points naming a question left open or an idea not finished.
Base these only on what the notes actually say.

Rules:
- Only use the notes above. Invent nothing.
- Every [[link]] must be an exact title from the notes above.
- No preamble, no closing remarks. Start at "## What you worked on"."""


def main() -> int:
    args = common.parse_args("FR10 - write a weekly digest note into the vault")
    common.banner("FR10  weekly digest", args.apply)

    notes = common.load()
    if not notes:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    recent = [n for n in notes
              if n.modified >= cutoff and n.domain != DIGEST_DOMAIN]
    if args.limit:
        recent = recent[: args.limit]

    if not recent:
        common.say(f"  no notes touched in the last {DAYS} days - nothing to digest")
        common.record("digest", args.apply, "no recent notes")
        return 0

    common.say(f"  {len(recent)} note(s) touched in the last {DAYS} days:")
    for n in recent:
        common.say(f"    - {n.title}  ({n.domain})")
    common.say("")

    # A busy week can exceed a free tier's per-request limit, so send the most
    # recently touched notes that fit and say plainly which were left out. A
    # digest that silently drops half the week is worse than one that admits it.
    included, size = [], 0
    for note in recent:
        cost = len(note.body[:NOTE_CHARS]) + len(note.title) + 40
        if included and size + cost > CHUNK_CHARS:
            break
        included.append(note)
        size += cost

    if len(included) < len(recent):
        common.say(f"  note budget reached: summarising the {len(included)} most "
                   f"recently touched of {len(recent)} notes")
        common.say("")

    blocks = "\n\n".join(
        f'--- NOTE "{n.title}" (domain: {n.domain}) ---\n{n.body[:NOTE_CHARS]}'
        for n in included
    )
    try:
        text = common.think(PROMPT.format(days=DAYS, notes=blocks))
    except common.llm.LLMError as exc:
        common.say(f"  ! LLM unavailable: {exc}")
        common.record("digest", args.apply, "llm unavailable")
        return 1

    # Drop links the model invented; a digest full of broken links is worse
    # than a digest with none.
    titles = {n.title for n in notes}
    import re
    invented = [t for t in re.findall(r"\[\[([^\]]+)\]\]", text) if t not in titles]
    for bad in invented:
        text = text.replace(f"[[{bad}]]", bad)
    if invented:
        common.say(f"  unlinked {len(invented)} invented reference(s): {', '.join(invented[:4])}")

    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    covered = ", ".join(f"[[{n.title}]]" for n in included)
    body = "\n".join([
        f"# Week {week}, {year} digest",
        "",
        f"*Covering {DAYS} days to {now:%d %B %Y}. "
        f"{len(included)} of {len(recent)} notes touched. "
        f"Written by Nautilus digest.py.*",
        "",
        text.strip(),
        "",
        "## Notes covered",
        "",
        covered,
        "",
    ])

    common.say("-" * 66)
    common.say(body)
    common.say("-" * 66)

    dest = common.config.VAULT_PATH / DIGEST_DOMAIN / f"{year}-W{week:02d}.md"
    common.write_note(dest, body, args.apply)
    if not args.apply:
        common.say("  re-run with --apply to write it into the vault")
    common.record("digest", args.apply, f"week {year}-W{week:02d}, {len(recent)} notes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
