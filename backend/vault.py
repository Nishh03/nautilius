"""Vault reader - satisfies FR1 to FR4.

Reads every markdown file under VAULT_PATH on demand. There is no cache and no
database: the vault is the single source of truth and is re-read per request,
so the dashboard can never show stale data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import config

WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+)(?:[#|][^\[\]]*)?\]\]")
HEADING_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Separate an Obsidian YAML frontmatter block from the note body.

    Only the subset Obsidian actually writes is parsed - `key: value` and
    `key: [a, b]` - because pulling in a YAML dependency to read six lines
    would cost more than it is worth. Anything unrecognised is ignored rather
    than guessed at.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    meta: dict[str, object] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not key:
            continue
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key] = value.strip("\"'")
    return meta, text[match.end():]


@dataclass
class Note:
    """One markdown file, parsed."""

    slug: str                 # stable id, path relative to vault without .md
    title: str                # first H1 heading, else prettified filename
    domain: str               # top-level folder = domain (FR1, zero config)
    path: Path
    modified: datetime
    body: str = field(repr=False, default="")        # frontmatter stripped
    links: list[str] = field(default_factory=list)   # outgoing wikilink targets
    tags: list[str] = field(default_factory=list)    # from YAML frontmatter
    meta: dict = field(repr=False, default_factory=dict)
    raw: str = field(repr=False, default="")         # the file exactly as on disk

    def to_dict(self, include_body: bool = False) -> dict:
        data = {
            "slug": self.slug,
            "title": self.title,
            "domain": self.domain,
            "modified": self.modified.isoformat(),
            "links": self.links,
            "tags": self.tags,
            "words": len(self.body.split()),
        }
        if include_body:
            data["body"] = self.body
        return data


def _title_from(body: str, path: Path) -> str:
    """First H1 wins; otherwise turn the filename into something readable."""
    match = HEADING_RE.search(body)
    if match:
        return match.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def _domain_from(path: Path, root: Path) -> str:
    """The first folder under the vault is the domain. Root notes are unfiled."""
    parts = path.relative_to(root).parts
    return parts[0] if len(parts) > 1 else config.UNFILED_DOMAIN


def _slug_from(path: Path, root: Path) -> str:
    return path.relative_to(root).with_suffix("").as_posix()


def read_note(path: Path, root: Path) -> Note:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = split_frontmatter(raw)
    tags = meta.get("tags") or meta.get("tag") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(",", " ").split() if t.strip()]
    return Note(
        slug=_slug_from(path, root),
        title=_title_from(body, path),
        domain=_domain_from(path, root),
        path=path,
        modified=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
        body=body,
        links=[t.strip() for t in WIKILINK_RE.findall(body)],
        tags=[str(t).lstrip("#") for t in tags],
        meta=meta,
        raw=raw,
    )


def _domains_from_tags(notes: list[Note]) -> None:
    """Group a flat vault by tag when there are no folders to group by.

    A vault kept as one flat folder - which Obsidian encourages - would put
    every note in `unfiled` and leave the orbit a single circle. Where such a
    note carries frontmatter tags, its first *distinguishing* tag becomes its
    domain instead.

    Tags shared by every note are skipped: a tag everyone has separates no one,
    and is usually just the vault's own name.
    """
    unfiled = [n for n in notes if n.domain == config.UNFILED_DOMAIN and n.tags]
    if not unfiled:
        return

    freq: dict[str, int] = {}
    for note in unfiled:
        for tag in set(note.tags):
            freq[tag] = freq.get(tag, 0) + 1

    universal = {t for t, c in freq.items() if c == len(unfiled)} if len(unfiled) > 1 else set()
    for note in unfiled:
        for tag in note.tags:
            if tag not in universal:
                note.domain = tag
                break


def load_notes(root: Path | None = None) -> list[Note]:
    """FR1 + FR2 - every note in the vault, newest first."""
    root = root or config.VAULT_PATH
    if not root.exists():
        return []
    notes = [
        read_note(p, root)
        for p in sorted(root.rglob("*.md"))
        if p.is_file() and not any(part.startswith(".") for part in p.parts)
    ]
    _domains_from_tags(notes)
    notes.sort(key=lambda n: n.modified, reverse=True)
    return notes


def domain_counts(notes: list[Note]) -> list[dict]:
    """FR3 - how many notes each domain holds, biggest first."""
    counts: dict[str, int] = {}
    for note in notes:
        counts[note.domain] = counts.get(note.domain, 0) + 1
    return [
        {"domain": d, "count": c}
        for d, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _resolve(target: str, notes: list[Note]) -> Note | None:
    """Match a wikilink target to a note by title or slug, case-insensitively."""
    key = target.strip().lower()
    for note in notes:
        if note.title.lower() == key or note.slug.lower() == key:
            return note
    for note in notes:                      # fall back to bare filename
        if note.slug.rsplit("/", 1)[-1].lower() == key:
            return note
    return None


def build_graph(notes: list[Note]) -> dict:
    """FR4 - the wikilink graph, with broken links called out."""
    edges, broken = [], []
    for note in notes:
        for target in note.links:
            hit = _resolve(target, notes)
            if hit:
                edges.append({"source": note.slug, "target": hit.slug})
            else:
                broken.append({"source": note.slug, "target": target})

    linked = {e["source"] for e in edges} | {e["target"] for e in edges}
    return {
        "nodes": [
            {"slug": n.slug, "title": n.title, "domain": n.domain,
             "degree": sum(e["source"] == n.slug or e["target"] == n.slug for e in edges)}
            for n in notes
        ],
        "edges": edges,
        "broken": broken,
        "orphans": sorted(n.slug for n in notes if n.slug not in linked),
    }
