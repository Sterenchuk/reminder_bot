"""Chat command handling. Text in, reply text out, so it is trivial to test."""
import re
import calendar
from datetime import datetime, timedelta

from . import db
from .schedule import from_iso, next_occurrence, once_at, parse_hhmm, to_iso

MAX_TEXT = 300
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DURATION = re.compile(r"(\d+)(mo|m|w|d|h)")

HELP = """Reminder bot

/add HH:MM text        every day
/weekdays HH:MM text   Monday to Friday
/once HH:MM text       one time (next time that clock hits)
/once YYYY-MM-DD HH:MM text   one time on a date
/list                  show your reminders
/snooze ID [duration]  snooze (10m default; e.g. 20m, 1h30m, 1d, 1w, 1mo)
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


def _snooze_duration(value: str) -> tuple[int, int]:
    """Return calendar months and elapsed minutes from a duration expression."""
    if value.isdigit():
        value = f"{value}m"
    parts = list(_DURATION.finditer(value))
    if not parts or "".join(part.group(0) for part in parts) != value:
        raise ValueError("invalid snooze duration")
    if any(int(part.group(1)) < 1 for part in parts):
        raise ValueError("snooze duration components must be positive")

    months = minutes = 0
    for part in parts:
        amount, unit = int(part.group(1)), part.group(2)
        if unit == "mo":
            months += amount
        else:
            minutes += amount * {"m": 1, "h": 60, "d": 1440, "w": 10080}[unit]
    return months, minutes


def _add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.year * 12 + dt.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _snooze(path, chat_id, rest, now, tz) -> str:
    parts = rest.split()
    if len(parts) not in (1, 2):
        return "Usage: /snooze ID [duration]"
    reminder_id = parts[0].lstrip("#")
    if not reminder_id.isdigit():
        return "Usage: /snooze ID [duration]"
    duration = "10m"
    duration_label = "10 minutes"
    if len(parts) == 2:
        duration = parts[1]
        duration_label = f"{duration} minutes" if duration.isdigit() else duration
    try:
        months, minutes = _snooze_duration(duration)
    except ValueError:
        return "Snooze duration must use positive values (e.g. 20m, 1h30m, 1d, 1w, 1mo)."
    next_run = _add_months(now.astimezone(tz), months).astimezone(now.tzinfo)
    next_run += timedelta(minutes=minutes)
    if not db.snooze_reminder(path, chat_id, int(reminder_id), to_iso(next_run)):
        return f"No reminder #{reminder_id}"
    return f"Snoozed #{reminder_id} for {duration_label}. Next: {_fmt_local(next_run, tz)}"


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
