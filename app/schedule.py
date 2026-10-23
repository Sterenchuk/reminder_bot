"""Pure time logic: no I/O, easy to unit test."""
import re
from datetime import date, datetime, time, timedelta, timezone

UTC = timezone.utc
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime(ISO_FMT)


def from_iso(s: str) -> datetime:
    return datetime.strptime(s, ISO_FMT).replace(tzinfo=UTC)


def parse_hhmm(text: str) -> str:
    """'8:30' -> '08:30'. Raises ValueError on bad input."""
    m = _HHMM.match(text.strip())
    if not m:
        raise ValueError("time must look like 08:30")
    hour, minute = int(m.group(1)), int(m.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("time out of range")
    return f"{hour:02d}:{minute:02d}"


def next_occurrence(kind: str, hhmm: str, after: datetime, tz) -> datetime:
    """First moment strictly after `after` (UTC) matching the rule, returned in UTC.

    kind: 'once' / 'daily' -> any day, 'weekdays' -> Monday to Friday only.
    Wall-clock time is interpreted in `tz`, so DST changes are handled.
    """
    hour, minute = int(hhmm[:2]), int(hhmm[3:])
    start = after.astimezone(tz).date()
    for offset in range(8):
        day = start + timedelta(days=offset)
        if kind == "weekdays" and day.weekday() >= 5:
            continue
        candidate = datetime.combine(day, time(hour, minute), tzinfo=tz).astimezone(UTC)
        if candidate > after:
            return candidate
    raise RuntimeError("no occurrence found")  # unreachable


def once_at(day: str, hhmm: str, tz) -> datetime:
    """Specific date 'YYYY-MM-DD' + time -> UTC datetime. Raises ValueError."""
    d = date.fromisoformat(day)
    hour, minute = int(hhmm[:2]), int(hhmm[3:])
    return datetime.combine(d, time(hour, minute), tzinfo=tz).astimezone(UTC)
