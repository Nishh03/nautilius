"""Applications agent - how many jobs you have applied to, and today's number.

    python automation/tracker.py            # report only
    python automation/tracker.py --apply    # also write the tracker note

LinkedIn has no public API for applications or connections, and scraping it
breaks their terms and gets accounts restricted. So the source of truth is the
same as everything else here: plain markdown notes you write.

Drop a note in the `applications` domain per application, with frontmatter:

    ---
    tags: [application]
    company: Acme
    role: ML Engineer
    status: applied        # applied | screening | interview | offer | rejected
    date: 2026-09-27
    ---

The agent counts them, compares against a weekly target, and works out how many
are still owed today - including catching up if you are behind.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import common

DOMAIN = "applications"
WEEKLY_TARGET = 10          # applications per week
WORKING_DAYS = 5            # spread across the working week

OPEN = {"applied", "screening", "interview"}
LIVE_ORDER = ["applied", "screening", "interview", "offer", "rejected"]


def applications(notes: list) -> list[dict]:
    """Every application note, newest first, with its fields pulled out."""
    out = []
    for n in notes:
        is_app = n.domain == DOMAIN or "application" in [t.lower() for t in n.tags]
        if not is_app:
            continue
        meta = n.meta or {}
        raw = str(meta.get("date", "")).strip()
        try:
            when = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            when = n.modified          # fall back to the file's own timestamp
        out.append({
            "title": n.title,
            "company": str(meta.get("company", "") or "?"),
            "role": str(meta.get("role", "") or "?"),
            "status": str(meta.get("status", "applied")).lower().strip(),
            "when": when,
            "slug": n.slug,
        })
    out.sort(key=lambda a: a["when"], reverse=True)
    return out


def main() -> int:
    args = common.parse_args("Applications - weekly target and today's number")
    common.banner("APPLICATIONS  target vs sent", args.apply)

    notes = common.load()
    apps = applications(notes)

    if not apps:
        common.say(f"  No application notes found.\n")
        common.say(f"  Create {DOMAIN}/ notes with `tags: [application]` and a")
        common.say(f"  company, role, status and date in the frontmatter, and this")
        common.say(f"  agent will start tracking them.")
        common.record("tracker", args.apply, "no applications yet")
        return 0

    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    this_week = [a for a in apps if a["when"] >= week_start]
    today = [a for a in apps if a["when"].date() == now.date()]

    by_status: dict[str, int] = {}
    for a in apps:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1

    # How many are still owed today: what is left this week, spread over the
    # days that remain, so falling behind on Monday raises Tuesday's number
    # rather than quietly disappearing.
    remaining = max(WEEKLY_TARGET - len(this_week), 0)
    days_left = max(WORKING_DAYS - min(now.weekday(), WORKING_DAYS - 1), 1)
    owed_today = max(-(-remaining // days_left) - len(today), 0)   # ceil, minus done

    common.say(f"  {len(apps)} application(s) tracked · {len(this_week)} this week "
               f"· target {WEEKLY_TARGET}")
    common.say("")
    for st in LIVE_ORDER:
        if by_status.get(st):
            common.say(f"    {st:<10} {by_status[st]}")
    common.say("")

    live = [a for a in apps if a["status"] in OPEN]
    if live:
        common.say(f"  Still live ({len(live)}):")
        for a in live[:8]:
            common.say(f"    {a['when']:%d %b}  {a['company']:<18} {a['role']:<24} {a['status']}")
        common.say("")

    if owed_today:
        common.say(f"  >>> SEND {owed_today} MORE TODAY  "
                   f"({remaining} left this week, {days_left} day(s) to do it)")
    else:
        common.say(f"  >>> Today is covered. {remaining} left to hit this week's target.")

    body = "\n".join([
        f"# Applications - week of {week_start:%d %B %Y}",
        "",
        f"*{len(this_week)} sent this week against a target of {WEEKLY_TARGET}. "
        f"Written by Nautilus tracker.py.*",
        "",
        "## Today",
        "",
        (f"Send **{owed_today}** more today." if owed_today
         else "Today's quota is met."),
        "",
        "## Still live",
        "",
        *([f"- [[{a['title']}]] — {a['company']}, {a['role']} ({a['status']})"
           for a in live[:12]] or ["Nothing open."]),
        "",
    ])
    dest = common.config.VAULT_PATH / DOMAIN / f"week-{week_start:%Y-%m-%d}.md"
    common.say("")
    common.write_note(dest, body, args.apply)
    if not args.apply:
        common.say("  dry run - re-run with --apply to write this into the vault")

    common.record("tracker", args.apply,
                  f"{len(this_week)}/{WEEKLY_TARGET} this week, {owed_today} owed today")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
