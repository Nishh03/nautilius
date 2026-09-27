"""The agent registry - the one place that knows what agents exist.

Everything else reads from here: the scheduler, the dashboard console, and the
API. Adding an agent means adding a row to AGENTS and writing the script; no
other file needs to change.

Each agent obeys the same contract, enforced by common.py:
  * dry run unless --apply is passed
  * never overwrites a file, never deletes one
  * anything the model invents is dropped before it reaches the vault
  * every run, in either mode, appends to history.log
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    name: str          # script stem, and the key used in history.log
    label: str         # shown in the console
    blurb: str         # one line: what it does for the user
    schedule: str      # human-readable; mirrored in schedule.bat
    cron: str          # what schedule.bat registers
    network: bool = False   # does it need the internet?
    writes: bool = True     # does it write into the vault?
    slow: bool = False      # can it take minutes on a free tier?


AGENTS: list[Agent] = [
    Agent(
        name="organize",
        label="Organise",
        blurb="Files rough captures from inbox into the right domain, with tags and links.",
        schedule="Nightly · 02:00",
        cron="/SC DAILY /ST 02:00",
    ),
    Agent(
        name="digest",
        label="Digest",
        blurb="Writes a summary of the week's notes, with threads left to pick up.",
        schedule="Mondays · 07:00",
        cron="/SC WEEKLY /D MON /ST 07:00",
    ),
    Agent(
        name="conflicts",
        label="Conflicts",
        blurb="Flags notes that contradict each other, quoting both sides.",
        schedule="Sundays · 20:00",
        cron="/SC WEEKLY /D SUN /ST 20:00",
        slow=True,
    ),
    Agent(
        name="progress",
        label="Progress",
        blurb="Snapshots how the vault is growing, so the trend can be charted.",
        schedule="Daily · 23:30",
        cron="/SC DAILY /ST 23:30",
        writes=False,
    ),
    Agent(
        name="radar",
        label="Radar",
        blurb="Pulls new AI/ML research and posts, keeps what matches your notes.",
        schedule="Daily · 08:00",
        cron="/SC DAILY /ST 08:00",
        network=True,
    ),
    Agent(
        name="tracker",
        label="Applications",
        blurb="Counts job applications against your weekly target and sets today's number.",
        schedule="Daily · 09:00",
        cron="/SC DAILY /ST 09:00",
    ),
    Agent(
        name="coach",
        label="Interview coach",
        blurb="Builds interview questions from your own notes and tracks the weak areas.",
        schedule="Tue & Fri · 18:00",
        cron="/SC WEEKLY /D TUE,FRI /ST 18:00",
    ),
]

BY_NAME = {a.name: a for a in AGENTS}


def exists(name: str) -> bool:
    return name in BY_NAME
