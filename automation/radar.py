"""Radar - what is new in AI/ML that is actually relevant to you.

    python automation/radar.py            # show what it found
    python automation/radar.py --apply    # write the briefing into the vault

A feed reader shows you everything and is therefore useless. This one scores
each item against the notes you have already written, using the same keyword
retrieval that answers your questions, and keeps only what connects to what you
are studying. Relevance is measured against your vault, not against a general
idea of "important".

This is the one agent that reaches the internet, which is a deliberate
exception to the local-first rule: public feeds come in, notes never go out.
Everything it fetches is a public RSS feed with no key and no account.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

import common

FEEDS = [
    ("arXiv cs.LG", "https://export.arxiv.org/rss/cs.LG"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
]

DOMAIN = "radar"
KEEP = 6                 # items kept per run
MIN_SCORE = 1.5          # below this an item is not really about your topics
TIMEOUT = 20.0

TAGS = re.compile(r"<[^>]+>")

PROMPT = """Below are notes a learner has written, then new items from AI/ML feeds today.

--- WHAT THEY ARE STUDYING ---
{topics}

--- NEW ITEMS ---
{items}

For EACH item, write one sentence saying what it is, and one sentence saying
why it connects to what they are studying. Be concrete and do not flatter the
item - if it is only loosely related, say so plainly.

Reply with ONLY a JSON array, same order as the items:

[{{"title": "the exact item title",
   "what": "one sentence on what it is",
   "why": "one sentence on how it connects to their notes"}}]

No prose, no code fence, only the JSON array."""


def clean(text: str) -> str:
    return TAGS.sub(" ", text or "").replace("&nbsp;", " ").strip()


def fetch(name: str, url: str) -> list[dict]:
    """Pull one RSS feed. A dead feed is skipped, never fatal."""
    try:
        r = httpx.get(url, timeout=TIMEOUT,
                      headers={"User-Agent": "Nautilus/0.1 (personal study tool)"},
                      follow_redirects=True)
    except httpx.RequestError as exc:
        common.say(f"    {name}: unreachable ({type(exc).__name__})")
        return []
    if r.status_code != 200:
        common.say(f"    {name}: HTTP {r.status_code}")
        return []

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as exc:
        common.say(f"    {name}: could not parse ({exc})")
        return []

    items = []
    # RSS puts entries at channel/item; Atom uses a namespaced <entry>.
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        get = lambda k: next(
            (clean(c.text) for c in node
             if c.tag.rsplit("}", 1)[-1] == k and c.text), "")
        link = get("link")
        if not link:
            for c in node:
                if c.tag.rsplit("}", 1)[-1] == "link":
                    link = c.attrib.get("href", "")
                    break
        title = get("title")
        if not title:
            continue
        items.append({
            "source": name,
            "title": title,
            "link": link,
            "summary": (get("description") or get("summary"))[:700],
        })
    common.say(f"    {name}: {len(items)} item(s)")
    return items


def main() -> int:
    args = common.parse_args("Radar - relevant AI/ML news, scored against your vault")
    common.banner("RADAR  what is new and relevant", args.apply)

    notes = common.load()
    if not notes:
        return 0

    study = [n for n in notes
             if n.domain in {"llm", "ml", "deep-learning", "mlops", "foundations"}]
    if not study:
        study = notes

    common.say("  Fetching public feeds (no key, no account):")
    items = [it for name, url in FEEDS for it in fetch(name, url)]
    if not items:
        common.say("\n  No feeds reachable - offline, or every source is down.")
        common.say("  Nothing written. This agent is the only one that needs a network.")
        common.record("radar", args.apply, "no feeds reachable")
        return 1
    common.say("")

    # Reuse the retrieval scorer: an item is relevant when it scores against
    # the vocabulary of the notes already written. No second ranking model.
    import retrieve
    idf = retrieve._idf(study)
    scored = []
    for it in items:
        terms = retrieve.tokenize(it["title"] + " " + it["summary"])
        if not terms:
            continue
        best, hit = 0.0, None
        for n in study:
            sc = retrieve.score_note(n, terms, idf)
            if sc > best:
                best, hit = sc, n
        if best >= MIN_SCORE:
            scored.append({**it, "score": round(best, 2), "matches": hit.title})
    scored.sort(key=lambda x: x["score"], reverse=True)
    keep = scored[:KEEP]

    common.say(f"  {len(items)} item(s) fetched, {len(scored)} matched your notes, "
               f"keeping the top {len(keep)}")
    if not keep:
        common.say("\n  Nothing today connects to what you are studying.")
        common.record("radar", args.apply, f"{len(items)} fetched, 0 relevant")
        return 0

    common.say("")
    for it in keep:
        common.say(f"    {it['score']:>5}  {it['title'][:64]}")
        common.say(f"           {it['source']} · closest note: {it['matches']}")
    common.say("")

    topics = ", ".join(sorted({n.title for n in study})[:40])
    blocks = "\n\n".join(
        f'--- ITEM "{it["title"]}" ({it["source"]}) ---\n{it["summary"][:500]}'
        for it in keep)
    result = common.ask_json(PROMPT.format(topics=topics, items=blocks), fallback=[])

    notes_by_title = {it["title"].lower(): it for it in keep}
    briefs = []
    if isinstance(result, list):
        briefs = [b for b in result
                  if isinstance(b, dict) and str(b.get("title", "")).lower() in notes_by_title]
    if isinstance(result, common.Unchecked):
        common.say("  ! model unavailable - writing the list without summaries")

    now = datetime.now(timezone.utc)
    lines = [
        f"# Radar - {now:%d %B %Y}",
        "",
        f"*{len(keep)} item(s) from public AI/ML feeds, kept because they score "
        f"against notes already in this vault. Written by Nautilus radar.py.*",
        "",
    ]
    for it in keep:
        b = next((x for x in briefs if x["title"].lower() == it["title"].lower()), None)
        lines += [f"## {it['title']}", ""]
        if b:
            lines += [str(b.get("what", "")).strip(), "",
                      f"**Why it matters to you:** {str(b.get('why','')).strip()}", ""]
        lines += [f"Source: {it['source']}" + (f" · <{it['link']}>" if it["link"] else ""),
                  f"Closest note: [[{it['matches']}]]", ""]

    body = "\n".join(lines)
    dest = common.config.VAULT_PATH / DOMAIN / f"{now:%Y-%m-%d}.md"
    common.write_note(dest, body, args.apply)
    if not args.apply:
        common.say("  dry run - re-run with --apply to write this into the vault")

    common.record("radar", args.apply,
                  f"{len(items)} fetched, {len(keep)} kept, {len(briefs)} summarised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
