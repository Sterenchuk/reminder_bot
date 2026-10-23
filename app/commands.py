"""Chat command handling. Text in, reply text out, so it is trivial to test."""
import re
from datetime import datetime, timedelta

from . import db
from .schedule import from_iso, next_occurrence, once_at, parse_hhmm, to_iso

MAX_TEXT = 300
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

HELP = """Reminder bot

/add HH:MM text        every day
/weekdays HH:MM text   Monday to Friday
/once HH:MM text       one time (next time that clock hits)
/once YYYY-MM-DD HH:MM text   one time on a date
/list                  show your reminders
/snooze ID [minutes]   snooze a reminder (10 minutes by default)
/del ID                delete a reminder

Example: /weekdays 09:00 Standup"""

_LABEL = {"once": "once", "daily": "daily", "weekdays": "Mon-Fri"}


def _fmt_local(dt_utc: datetime, tz) -> str:
    return dt_utc.astimezone(tz).strftime("%a %d %b %H:%M")


def _create(path, chat_id, kind, rest, now, tz) -> str:
    parts = rest.split()
    date_part = None
    if kind == "once" and parts and _DATE.match(parts[0]):
        date_part = parts.pop(0)
    if len(parts) < 2:
        return "Usage: see /help"
    try:
        hhmm = parse_hhmm(parts[0])
    except ValueError:
        return "Time must look like 08:30 (24h)."
    body = " ".join(parts[1:])
    if len(body) > MAX_TEXT:
        return f"Text too long (max {MAX_TEXT} characters)."

    if date_part:
        try:
            run = once_at(date_part, hhmm, tz)
        except ValueError:
            return "Date must look like 2026-11-02."
        if run <= now:
            return "That moment is already in the past."
    else:
        run = next_occurrence(kind, hhmm, now, tz)

    rid = db.add_reminder(path, chat_id, body, kind, hhmm, to_iso(run))
    return f"Saved #{rid} ({_LABEL[kind]} {hhmm}): {body}\nNext: {_fmt_local(run, tz)}"


def _list(path, chat_id, tz) -> str:
    rows = db.list_reminders(path, chat_id)
    if not rows:
        return "No reminders yet. Try /add 08:30 Take vitamins"
    lines = []
    for r in rows:
        nxt = _fmt_local(from_iso(r["next_run"]), tz)
        lines.append(f"#{r['id']} [{_LABEL[r['kind']]} {r['at_time']}] {r['text']} (next {nxt})")
    return "\n".join(lines)


def _delete(path, chat_id, rest) -> str:
    rest = rest.lstrip("#")
    if not rest.isdigit():
        return "Usage: /del ID"
    if db.delete_reminder(path, chat_id, int(rest)):
        return f"Deleted #{rest}"
    return f"No reminder #{rest}"


def _snooze(path, chat_id, rest, now, tz) -> str:
    parts = rest.split()
    if len(parts) not in (1, 2):
        return "Usage: /snooze ID [minutes]"
    reminder_id = parts[0].lstrip("#")
    if not reminder_id.isdigit():
        return "Usage: /snooze ID [minutes]"
    minutes = 10
    if len(parts) == 2:
        if not parts[1].isdigit() or int(parts[1]) < 1:
            return "Snooze duration must be a positive number of minutes."
        minutes = int(parts[1])
    next_run = now + timedelta(minutes=minutes)
    if not db.snooze_reminder(path, chat_id, int(reminder_id), to_iso(next_run)):
        return f"No reminder #{reminder_id}"
    return f"Snoozed #{reminder_id} for {minutes} minutes. Next: {_fmt_local(next_run, tz)}"


def handle_text(path: str, chat_id: int, text: str, now: datetime, tz) -> str:
    cmd, _, rest = text.strip().partition(" ")
    cmd = cmd.split("@")[0].lower()  # "/add@MyBot" in group chats
    rest = rest.strip()

    if cmd in ("/start", "/help"):
        return HELP
    if cmd == "/add":
        return _create(path, chat_id, "daily", rest, now, tz)
    if cmd == "/weekdays":
        return _create(path, chat_id, "weekdays", rest, now, tz)
    if cmd == "/once":
        return _create(path, chat_id, "once", rest, now, tz)
    if cmd == "/list":
        return _list(path, chat_id, tz)
    if cmd == "/snooze":
        return _snooze(path, chat_id, rest, now, tz)
    if cmd in ("/del", "/delete"):
        return _delete(path, chat_id, rest)
    return "Unknown command. Try /help"
