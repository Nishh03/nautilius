"""FR11 - conflict check: flag notes that contradict each other.

    python automation/conflicts.py            # dry run - prints the report
    python automation/conflicts.py --apply    # write the report into the vault

Notes are compared within each domain, because that is where genuine
contradictions live and it keeps the work proportional to the vault rather than
quadratic in it.

The hard part is not finding contradictions - it is not inventing them. A model
asked "find the contradictions" will always find some. The prompt therefore
defines what does NOT count, demands a quote from each side, and treats an
empty list as the expected answer.
"""
from __future__ import annotations

from datetime import datetime, timezone

import common

REPORT_DOMAIN = "reviews"
MIN_NOTES = 2
NOTE_CHARS = 1200      # per note sent to the model
CHUNK_CHARS = 9000     # per request; sized for a free tier's per-minute cap

PROMPT = """Below are notes from one domain of a personal knowledge vault.

{notes}

Find pairs of notes that genuinely CONTRADICT each other - where believing one
means the other must be wrong.

This does NOT count as a contradiction:
- two notes covering different topics
- one note being more detailed than another
- a note describing a plan and another describing the current state
- a trade-off discussed from two angles
- a note describing something as an upgrade path or future option

Reply with ONLY a JSON array. For each real contradiction:

[{{"note_a": "exact title", "quote_a": "the exact sentence from note A",
   "note_b": "exact title", "quote_b": "the exact sentence from note B",
   "conflict": "one sentence on why these cannot both be true"}}]

If there are no genuine contradictions, reply with exactly: []
Most domains have none. An empty array is the correct and expected answer."""


def main() -> int:
    args = common.parse_args("FR11 - flag notes that contradict each other")
    common.banner("FR11  conflict check", args.apply)

    notes = common.load()
    if not notes:
        return 0

    domains: dict[str, list] = {}
    for n in notes:
        if n.domain != REPORT_DOMAIN:
            domains.setdefault(n.domain, []).append(n)

    titles = {n.title for n in notes}
    by_title = {n.title: n for n in notes}
    found: list[dict] = []
    checked = 0
    unchecked = 0

    def scan(label: str, group: list, warn_split: bool = True) -> tuple[list[dict], int]:
        """Compare one group of notes. Returns (contradictions, chunks_failed).

        Free-tier providers cap tokens per minute, so a large group is split
        into chunks that fit. Splitting means pairs separated across chunks are
        never compared - that is a real reduction in coverage, so it is printed
        rather than hidden.
        """
        chunks, current, size = [], [], 0
        for note in group:
            cost = len(note.body[:NOTE_CHARS]) + len(note.title) + 40
            if current and size + cost > CHUNK_CHARS:
                chunks.append(current)
                current, size = [], 0
            current.append(note)
            size += cost
        if current:
            chunks.append(current)

        if len(chunks) > 1 and warn_split:
            common.say(f"  {label}: split into {len(chunks)} request(s) to fit the "
                       f"provider limit - pairs split across chunks are not compared")

        clean, failed = [], 0
        for chunk in chunks:
            if len(chunk) < MIN_NOTES:
                continue
            blocks = "\n\n".join(
                f'--- NOTE "{n.title}" ---\n{n.body[:NOTE_CHARS]}' for n in chunk
            )
            result = common.ask_json(PROMPT.format(notes=blocks), fallback=[])
            if isinstance(result, common.Unchecked):
                failed += 1
                continue
            if isinstance(result, dict):
                result = [result]
            if not isinstance(result, list):
                result = []

            for item in result:
                if not isinstance(item, dict):
                    continue
                a, b = item.get("note_a"), item.get("note_b")
                if a in titles and b in titles and a != b:
                    item["domain"] = label
                    clean.append(item)
                else:
                    common.say(f"  ! discarded a pair naming unknown notes: {a} / {b}")
        return clean, failed

    for domain, group in sorted(domains.items()):
        if len(group) < MIN_NOTES:
            common.say(f"- {domain}: only {len(group)} note, skipped")
            continue
        if args.limit and checked >= args.limit:
            break
        checked += 1

        clean, failed = scan(domain, group)
        unchecked += failed
        status = (f"{len(clean) or 'no'} contradiction(s)" if not failed
                  else f"NOT CHECKED - {failed} request(s) failed")
        common.say(f"- {domain}: {len(group)} notes -> {status}")
        found.extend(clean)

    # Contradictions do not respect folders. A plan in one domain can disagree
    # with a conclusion reached in another, and comparing every note against
    # every other is quadratic - so use the vault's own wikilinks as the hint
    # that two notes are about the same thing.
    seen: set[tuple[str, str]] = set()
    linked: list[tuple] = []
    for note in notes:
        for target in note.links:
            other = by_title.get(target)
            if not other or other.domain == note.domain:
                continue
            key = tuple(sorted((note.title, other.title)))
            if key in seen:
                continue
            seen.add(key)
            linked.append((note, other))

    if linked:
        # Chunk by PAIR, not by note. Splitting a flat note list can put the two
        # halves of a linked pair into different requests, so the one comparison
        # that pair existed for never happens - which is how this missed the
        # clearest contradiction in the vault on the first run.
        batches, current, size = [], {}, 0
        for a, b in linked:
            cost = sum(len(n.body[:NOTE_CHARS]) for n in (a, b) if n.title not in current)
            if current and size + cost > CHUNK_CHARS:
                batches.append(list(current.values()))
                current, size = {}, 0
                cost = len(a.body[:NOTE_CHARS]) + len(b.body[:NOTE_CHARS])
            current[a.title] = a
            current[b.title] = b
            size += cost
        if current:
            batches.append(list(current.values()))

        clean, failed = [], 0
        for batch in batches:
            # Batches are already pair-safe, so no split warning here.
            got, bad = scan("linked across domains", batch, warn_split=False)
            clean.extend(got)
            failed += bad
        unchecked += failed
        status = (f"{len(clean) or 'no'} contradiction(s)" if not failed
                  else f"NOT CHECKED - {failed} request(s) failed")
        common.say(f"- linked across domains: {len(seen)} linked pair(s) in "
                   f"{len(batches)} request(s) -> {status}")
        found.extend(clean)
        checked += 1

    common.say("")
    now = datetime.now(timezone.utc)

    if unchecked:
        common.say(f"  WARNING: {unchecked} request(s) could not be completed. "
                   f"Those notes were NOT checked - this is not a clean result.")

    if not found:
        verdict = ("no contradictions found - nothing to write" if not unchecked
                   else "no contradictions in the parts that were checked")
        common.say(f"  {verdict}")
        common.record("conflicts", args.apply,
                      f"{checked} groups, 0 found, {unchecked} unchecked")
        return 1 if unchecked else 0

    lines = [
        f"# Conflict check - {now:%d %B %Y}",
        "",
        f"*{len(found)} possible contradiction(s) across {checked} domain(s). "
        f"Written by Nautilus conflicts.py - review before acting.*",
        "",
    ]
    for i, c in enumerate(found, 1):
        lines += [
            f"## {i}. [[{c['note_a']}]] vs [[{c['note_b']}]]",
            "",
            f"**Domain:** {c.get('domain','?')}",
            "",
            f"**{c['note_a']}** says:",
            f"> {str(c.get('quote_a','')).strip()}",
            "",
            f"**{c['note_b']}** says:",
            f"> {str(c.get('quote_b','')).strip()}",
            "",
            f"**Why these clash:** {str(c.get('conflict','')).strip()}",
            "",
        ]

    body = "\n".join(lines)
    common.say("-" * 66)
    common.say(body)
    common.say("-" * 66)

    dest = common.config.VAULT_PATH / REPORT_DOMAIN / f"conflicts-{now:%Y-%m-%d}.md"
    common.write_note(dest, body, args.apply)
    if not args.apply:
        common.say("  re-run with --apply to write it into the vault")
    common.record("conflicts", args.apply,
                  f"{checked} groups, {len(found)} found, {unchecked} unchecked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
