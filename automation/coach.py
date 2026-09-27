"""Interview coach - questions built from your own notes.

    python automation/coach.py            # show the questions
    python automation/coach.py --apply    # write a practice note into the vault

Generic interview question lists are everywhere and are not worth much. What
makes this useful is that every question is answerable from a note you already
wrote, so practising doubles as revision, and a question you cannot answer
points at a note that is too thin.

Topics are chosen in this order:
  1. anything you flagged as weak in your own interview-prep notes
  2. topics in the stage of the roadmap you are currently on
  3. the thinnest notes, since a short note is usually a shallow understanding
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import common

CAREER_DOMAIN = "career"
PICK = 5                 # topics per session
THIN = 90                # words below which a note counts as thin

PROMPT = """You are preparing someone for an AI engineer interview using only their own notes.

{blocks}

For EACH note above, write one interview question that:
- can be answered from that note's content, and nothing else
- sounds like a real interviewer, not a textbook prompt
- targets the idea in the note that a candidate most often gets wrong

Reply with ONLY a JSON array, in the same order as the notes:

[{{"topic": "the exact note title",
   "question": "the question",
   "good_answer": "two sentences naming the points a strong answer must hit",
   "trap": "the mistake a weak candidate makes here"}}]

No prose, no code fence, only the JSON array."""


def weak_flags(notes: list) -> set[str]:
    """Topics the user marked weak in their own prep notes."""
    weak: set[str] = set()
    for n in notes:
        if n.domain != CAREER_DOMAIN:
            continue
        for line in n.body.splitlines():
            if "weak" not in line.lower():
                continue
            # "- Explain backprop - **weak**, I can describe it but not derive it"
            for target in re.findall(r"\[\[([^\]]+)\]\]", line):
                weak.add(target.strip().lower())
            # "- Explain backprop - **weak**, ..." -> "explain backprop".
            # Only the short head of a bullet counts; a whole sentence that
            # merely contains the word "weak" is prose, not a topic name.
            if not line.lstrip().startswith(("-", "*")):
                continue
            head = re.sub(r"^[-*\s]+", "", line).split(" - ")[0].strip(" *")
            if head and len(head.split()) <= 5 and not head.endswith((".", ":")):
                weak.add(head.lower())
    return weak


def choose(notes: list) -> list:
    """Pick the topics worth drilling, weakest signal first."""
    weak = weak_flags(notes)
    pool = [n for n in notes
            if n.domain not in {CAREER_DOMAIN, "inbox", "digests", "reviews",
                                "applications", "roadmap"}
            and len(n.body.split()) >= 25]

    def rank(n):
        title = n.title.lower()
        flagged = any(title == w or w in title or title in w for w in weak)
        return (0 if flagged else 1, len(n.body.split()))

    pool.sort(key=rank)
    return pool[:PICK], weak


def main() -> int:
    args = common.parse_args("Interview coach - questions from your own notes")
    common.banner("COACH  interview drill", args.apply)

    notes = common.load()
    if not notes:
        return 0

    picked, weak = choose(notes)
    if not picked:
        common.say("  Not enough written notes to build questions from yet.")
        common.record("coach", args.apply, "not enough notes")
        return 0

    if weak:
        common.say(f"  Flagged weak in your own prep notes: {', '.join(sorted(weak)[:5])}")
    common.say(f"  Drilling {len(picked)} topic(s):")
    for n in picked:
        thin = "  (thin)" if len(n.body.split()) < THIN else ""
        common.say(f"    {n.title:<38} {len(n.body.split()):>4} words{thin}")
    common.say("")

    blocks = "\n\n".join(
        f'--- NOTE "{n.title}" ---\n{n.body[:1100]}' for n in picked)
    result = common.ask_json(PROMPT.format(blocks=blocks), fallback=[])

    if isinstance(result, common.Unchecked):
        common.say(f"  ! could not reach the model - no questions generated")
        common.record("coach", args.apply, "llm unavailable")
        return 1
    if isinstance(result, dict):
        result = [result]

    titles = {n.title.lower(): n for n in notes}
    qs = [q for q in result
          if isinstance(q, dict) and str(q.get("topic", "")).lower() in titles]
    dropped = len(result) - len(qs)
    if dropped:
        common.say(f"  dropped {dropped} question(s) naming notes that do not exist")
    if not qs:
        common.say("  no usable questions came back")
        common.record("coach", args.apply, "no usable questions")
        return 1

    common.say("-" * 66)
    for i, q in enumerate(qs, 1):
        common.say(f"\n  Q{i}. [{q['topic']}]\n  {q['question']}")
        common.say(f"      strong answer: {str(q.get('good_answer','')).strip()[:200]}")
        common.say(f"      common trap  : {str(q.get('trap','')).strip()[:160]}")
    common.say("\n" + "-" * 66)

    now = datetime.now(timezone.utc)
    body = "\n".join([
        f"# Interview drill - {now:%d %B %Y}",
        "",
        f"*{len(qs)} question(s), each answerable from a note in this vault. "
        f"Written by Nautilus coach.py.*",
        "",
        *[line for i, q in enumerate(qs, 1) for line in [
            f"## {i}. {q['question']}",
            "",
            f"**From:** [[{q['topic']}]]",
            "",
            f"**A strong answer hits:** {str(q.get('good_answer','')).strip()}",
            "",
            f"**The usual trap:** {str(q.get('trap','')).strip()}",
            "",
        ]],
        "Related: [[Interview Prep - ML Theory]], [[Interview Prep - Coding]]",
        "",
    ])
    dest = common.config.VAULT_PATH / CAREER_DOMAIN / f"drill-{now:%Y-%m-%d}.md"
    common.write_note(dest, body, args.apply)
    if not args.apply:
        common.say("  dry run - re-run with --apply to write this into the vault")

    common.record("coach", args.apply, f"{len(qs)} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
