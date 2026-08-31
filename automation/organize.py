"""FR9 - auto-organise: file rough captures into the right domain.

Reads every note sitting in the capture folder (default: inbox/), asks the model
which existing domain it belongs to, then moves it there with tags and links to
related notes added at the top.

    python automation/organize.py            # dry run - shows the plan
    python automation/organize.py --apply    # actually move the files

The model may only choose from domains that already exist, plus one explicitly
offered new-domain slot. Left unconstrained it invents a new domain for every
note and the vault fragments instead of organising.
"""
from __future__ import annotations

import re
from pathlib import Path

import common

CAPTURE_DOMAIN = "inbox"          # where rough notes land
MIN_WORDS = 5                     # anything shorter has nothing to classify

PROMPT = """Below is a rough captured note, followed by the domains and notes that already exist.

--- THE CAPTURE ---
{capture}

--- EXISTING DOMAINS ---
{domains}

--- EXISTING NOTES ---
{menu}

Decide where this capture belongs. Reply with ONLY a JSON object:

{{"title": "a short specific title, 2-6 words",
  "domain": "one domain from the list above, or \\"{new_slot}\\" if it truly fits none",
  "tags": ["two", "or", "three", "lowercase-tags"],
  "links": ["exact titles of up to 3 existing notes that are genuinely related"]}}

Rules:
- Strongly prefer an existing domain. Only use "{new_slot}" if nothing fits.
- "links" must be exact titles copied from the EXISTING NOTES list, or [].
- No prose, no code fence, only the JSON object."""


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9\s-]", "", title.lower()).strip()
    return re.sub(r"[\s-]+", "-", s)[:60] or "untitled"


def vault_style(filed: list) -> tuple[bool, list[str]]:
    """Work out how this vault groups notes, so we file the way it already does.

    A vault that uses folders gets a note moved into a folder. A flat vault -
    which Obsidian encourages, and where domains come from frontmatter tags -
    gets a note written to the root with tags instead. Filing a tag-organised
    vault into folders would leave it grouped two incompatible ways at once.

    Also returns the tags every existing note carries, so a new note inherits
    the vault's own conventions rather than looking foreign next to them.
    """
    uses_folders = any("/" in n.slug for n in filed)
    tagged = [n for n in filed if n.tags]
    universal = [
        t for t in (tagged[0].tags if tagged else [])
        if all(t in n.tags for n in tagged)
    ] if len(tagged) > 1 else []
    return uses_folders, universal


def build_body(plan: dict, original: str, valid_titles: set[str],
               *, frontmatter_tags: list[str] | None = None) -> str:
    """Rewrite the capture as a filed note, keeping the original text intact."""
    title = plan.get("title") or "Untitled"
    tags = [str(t).strip().lstrip("#") for t in plan.get("tags") or [] if str(t).strip()]
    links = [l for l in (plan.get("links") or []) if l in valid_titles]

    # Strip a leading heading so we do not end up with two.
    text = re.sub(r"^\s*#\s+.*\n+", "", original, count=1).strip()

    parts: list[str] = []
    if frontmatter_tags is not None:
        # Flat, tag-organised vault: the tags carry the grouping, so they go in
        # frontmatter where Obsidian and the dashboard both read them.
        merged = list(dict.fromkeys(frontmatter_tags + tags))[:6]
        parts += ["---", f"tags: [{', '.join(merged)}]", "---", ""]
        parts += [f"# {title}", ""]
    else:
        parts += [f"# {title}", ""]
        if tags:
            parts += [" ".join("#" + t for t in tags[:4]), ""]

    parts += [text, ""]
    if links:
        parts += ["", "Related: " + ", ".join(f"[[{l}]]" for l in links[:3]), ""]
    parts += ["<!-- filed automatically by Nautilus organize.py -->"]
    return "\n".join(parts)


def main() -> int:
    args = common.parse_args("FR9 - file rough captures into the right domain")
    common.banner("FR9  auto-organise", args.apply)

    notes = common.load()
    if not notes:
        return 0

    captures = [n for n in notes if n.domain == CAPTURE_DOMAIN]
    if args.limit:
        captures = captures[: args.limit]
    if not captures:
        common.say(f"  nothing to file: {CAPTURE_DOMAIN}/ is empty")
        common.record("organize", args.apply, "no captures")
        return 0

    # The model chooses only from domains that already hold filed notes.
    domains = sorted({n.domain for n in notes} - {CAPTURE_DOMAIN})
    filed = [n for n in notes if n.domain != CAPTURE_DOMAIN]
    titles = {n.title for n in filed}
    new_slot = "NEW: <your suggested domain>"

    uses_folders, universal = vault_style(filed)
    how = "into folders" if uses_folders else "as tagged notes in the vault root"
    common.say(f"  {len(captures)} capture(s) to file {how}: "
               f"{', '.join(domains) or '(no domains yet)'}")
    if universal:
        common.say(f"  every note here carries: {', '.join(universal)} - new notes will too")
    common.say("")
    moved = 0

    for capture in captures:
        common.say(f"- {capture.slug}")
        if len(capture.body.split()) < MIN_WORDS:
            common.say("  skipped: too short to classify\n")
            continue

        plan = common.ask_json(
            PROMPT.format(
                capture=capture.body[:2000],
                domains="\n".join("- " + d for d in domains) or "(none yet)",
                menu=common.note_menu(filed) or "(none yet)",
                new_slot=new_slot,
            ),
            fallback=None,
        )
        if not isinstance(plan, dict) or not plan.get("domain"):
            common.say("  skipped: no usable plan from the model\n")
            continue

        domain = str(plan["domain"]).strip()
        if domain.startswith("NEW:"):
            domain = slugify(domain.split(":", 1)[1])
            common.say(f"  proposing a new domain: {domain}")
        elif domain not in domains:
            # The model ignored the list. Refuse rather than scatter notes.
            common.say(f"  skipped: '{domain}' is not an existing domain\n")
            continue

        name = f"{slugify(plan.get('title', ''))}.md"
        if uses_folders:
            body = build_body(plan, capture.body, titles)
            dest = common.config.VAULT_PATH / domain / name
        else:
            # Flat vault: the domain is a tag, so it leads the frontmatter.
            body = build_body(plan, capture.body, titles,
                              frontmatter_tags=universal + [domain])
            dest = common.config.VAULT_PATH / name

        common.say(f"  title:  {plan.get('title')}")
        common.say(f"  domain: {domain}")
        if plan.get("tags"):
            common.say(f"  tags:   {' '.join('#'+str(t).lstrip('#') for t in plan['tags'][:4])}")
        kept = [l for l in (plan.get("links") or []) if l in titles]
        if kept:
            common.say(f"  links:  {', '.join(kept[:3])}")
        dropped = [l for l in (plan.get("links") or []) if l not in titles]
        if dropped:
            common.say(f"  dropped invented links: {', '.join(dropped)}")

        target = common.write_note(dest, body, args.apply)
        if args.apply:
            capture.path.unlink()          # the content now lives at `target`
            common.say(f"  removed  {capture.slug}.md from {CAPTURE_DOMAIN}/")
        else:
            common.say(f"  would remove  {capture.slug}.md from {CAPTURE_DOMAIN}/")
        moved += 1
        common.say("")

    verb = "filed" if args.apply else "would file"
    common.say(f"  {verb} {moved} of {len(captures)} capture(s)")
    if not args.apply and moved:
        common.say("  re-run with --apply to make these changes")
    common.record("organize", args.apply, f"{moved}/{len(captures)} captures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
