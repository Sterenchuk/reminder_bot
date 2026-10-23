from datetime import datetime

import pytest

from app.schedule import UTC, next_occurrence, once_at, parse_hhmm, from_iso, to_iso
from tests.conftest import NOW, VIENNA


@pytest.mark.parametrize("raw,expected", [("8:30", "08:30"), ("08:05", "08:05"), ("23:59", "23:59")])
def test_parse_hhmm_ok(raw, expected):
    assert parse_hhmm(raw) == expected


@pytest.mark.parametrize("raw", ["25:00", "12:60", "abc", "8", "8:3", ""])
def test_parse_hhmm_bad(raw):
    with pytest.raises(ValueError):
        parse_hhmm(raw)


def test_daily_later_today():
    # 11:00 Vienna = 09:00 UTC, still ahead of NOW (08:00 UTC)
    assert next_occurrence("daily", "11:00", NOW, VIENNA) == datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def test_daily_already_passed_goes_tomorrow():
    # 09:00 Vienna today is 07:00 UTC, already past -> tomorrow
    assert next_occurrence("daily", "09:00", NOW, VIENNA) == datetime(2026, 10, 24, 7, 0, tzinfo=UTC)


def test_strictly_after():
    # exactly now must not fire again immediately
    assert next_occurrence("daily", "10:00", NOW, VIENNA) == datetime(2026, 10, 24, 8, 0, tzinfo=UTC)


def test_weekdays_skip_weekend_and_dst():
    # Friday after 09:00 -> Monday 26 Oct. DST ended, so 09:00 local is 08:00 UTC.
    assert next_occurrence("weekdays", "09:00", NOW, VIENNA) == datetime(2026, 10, 26, 8, 0, tzinfo=UTC)


def test_once_at_specific_date():
    assert once_at("2026-11-02", "18:45", VIENNA) == datetime(2026, 11, 2, 17, 45, tzinfo=UTC)


def test_once_at_bad_date():
    with pytest.raises(ValueError):
        once_at("2026-13-40", "10:00", VIENNA)


def test_iso_roundtrip():
    assert from_iso(to_iso(NOW)) == NOW
