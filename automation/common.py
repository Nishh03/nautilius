"""Shared helpers for the scheduled maintenance tasks (FR9-FR11).

These scripts are the only part of Nautilus that WRITES to the vault, so the
rules here are deliberately strict:

  * nothing happens without --apply; the default is always a dry run
  * a file is never overwritten and never deleted, only created or moved
  * every run appends to automation/history.log so an unattended task can be
    audited after the fact

The literature review flags that an agent which moves files must be supervised
before it runs unattended. Dry-run-by-default is that supervision.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# The backend modules are the single source of truth for reading the vault.
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

import config  # noqa: E402
import llm  # noqa: E402
import vault  # noqa: E402

HISTORY = Path(__file__).resolve().parent / "history.log"


# --- CLI --------------------------------------------------------------------

def parse_args(description: str) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--apply", action="store_true",
                   help="actually write to the vault (default is a dry run)")
    p.add_argument("--limit", type=int, default=0,
                   help="process at most N items (0 = no limit)")
    return p.parse_args()


# --- output -----------------------------------------------------------------

def banner(task: str, applying: bool) -> None:
    mode = "APPLY - writing to the vault" if applying else "DRY RUN - nothing will be written"
    print(f"\n{'=' * 66}\n  {task}\n  vault: {config.VAULT_PATH}\n  mode:  {mode}\n{'=' * 66}")


def say(msg: str) -> None:
    print(msg)


def record(task: str, applying: bool, summary: str) -> None:
    """Append one line to the audit log so unattended runs are reviewable."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    mode = "APPLY" if applying else "DRYRUN"
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp}  {task:<10} {mode:<7} {summary}\n")


# --- safe writes ------------------------------------------------------------

def unique_path(path: Path) -> Path:
    """Never clobber: alpha.md -> alpha-2.md -> alpha-3.md ..."""
    if not path.exists():
        return path
    for i in range(2, 500):
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot find a free filename near {path}")


def write_note(path: Path, body: str, applying: bool) -> Path:
    target = unique_path(path)
    rel = target.relative_to(config.VAULT_PATH)
    if applying:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        say(f"  written  {rel}")
    else:
        say(f"  would write  {rel}  ({len(body.split())} words)")
    return target


def move_note(src: Path, dest: Path, applying: bool) -> Path:
    target = unique_path(dest)
    if applying:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(target))
    arrow = "moved" if applying else "would move"
    say(f"  {arrow}  {src.relative_to(config.VAULT_PATH)}"
        f"  ->  {target.relative_to(config.VAULT_PATH)}")
    return target


# --- LLM helpers ------------------------------------------------------------

JSON_BLOCK = re.compile(r"\{.*\}|\[.*\]", re.S)


class Unchecked:
    """Returned when the model could not be consulted at all.

    Distinct from an empty result on purpose. "I checked and found nothing" and
    "I could not check" look identical to a caller that only sees `[]`, and
    reporting the second as the first is how an automated review silently
    stops reviewing. Callers must handle this explicitly.
    """

    def __init__(self, reason: str):
        self.reason = reason

    def __repr__(self):
        return f"Unchecked({self.reason!r})"


def ask_json(prompt: str, fallback):
    """Ask the model for JSON and parse it defensively.

    Small models wrap JSON in prose or code fences, so pull out the first
    JSON-looking block rather than trusting the whole response. A task that
    cannot parse a reply must degrade to doing nothing, never to guessing.

    Returns `Unchecked` if the provider could not be reached, so the caller can
    tell a clean result from a missing one.
    """
    try:
        raw = llm.complete(prompt)
    except llm.LLMError as exc:
        say(f"  ! LLM unavailable: {exc}")
        return Unchecked(str(exc)[:120]) if fallback is not None else fallback

    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?|```$", "", raw, flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = JSON_BLOCK.search(raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    say(f"  ! could not parse a JSON reply: {raw[:160]}")
    return fallback


def load() -> list:
    notes = vault.load_notes()
    if not notes:
        say(f"  vault is empty: {config.VAULT_PATH}")
    return notes


def note_menu(notes: list) -> str:
    """A compact title/domain listing the model can point at."""
    return "\n".join(f'- "{n.title}" (domain: {n.domain})' for n in notes)
