from datetime import datetime

from app import db
from app.commands import handle_text
from app.schedule import UTC
from tests.conftest import NOW, VIENNA

CHAT = 111


def run(path, text, chat=CHAT, now=NOW):
    return handle_text(path, chat, text, now, VIENNA)


def test_add_daily(path):
    reply = run(path, "/add 09:00 Take vitamins")
    assert "Saved #1" in reply
    rows = db.list_reminders(path, CHAT)
    assert len(rows) == 1
    assert rows[0]["kind"] == "daily"
    assert rows[0]["next_run"] == "2026-10-24T07:00:00Z"


def test_weekdays(path):
    run(path, "/weekdays 9:00 Standup")
    row = db.list_reminders(path, CHAT)[0]
    assert row["kind"] == "weekdays"
    assert row["next_run"] == "2026-10-26T08:00:00Z"


def test_once_today_and_dated(path):
    run(path, "/once 11:00 Call mom")
    run(path, "/once 2026-11-02 18:45 Dentist")
    rows = db.list_reminders(path, CHAT)
    assert [r["kind"] for r in rows] == ["once", "once"]
    assert rows[0]["next_run"] == "2026-10-23T09:00:00Z"


def test_once_in_the_past_rejected(path):
    assert "past" in run(path, "/once 2026-10-01 10:00 Old")
    assert db.list_reminders(path, CHAT) == []


def test_bad_input(path):
    assert "Time must look like" in run(path, "/add 25:00 x")
    assert "Usage" in run(path, "/add 09:00")
    assert "too long" in run(path, "/add 09:00 " + "x" * 400)
    assert db.list_reminders(path, CHAT) == []


def test_list_and_delete(path):
    run(path, "/add 09:00 A")
    assert "#1" in run(path, "/list")
    assert "Deleted #1" in run(path, "/del 1")
    assert "No reminders" in run(path, "/list")


def test_snooze_defaults_to_ten_minutes(path):
    run(path, "/add 09:00 A")

    reply = run(path, "/snooze 1")

    assert "Snoozed #1 for 10 minutes" in reply
    assert db.list_reminders(path, CHAT)[0]["next_run"] == "2026-10-23T08:10:00Z"


def test_snooze_custom_duration(path):
    run(path, "/add 09:00 A")

    reply = run(path, "/snooze #1 45")

    assert "Snoozed #1 for 45 minutes" in reply
    assert db.list_reminders(path, CHAT)[0]["next_run"] == "2026-10-23T08:45:00Z"


def test_snooze_validates_input_and_chat_ownership(path):
    run(path, "/add 09:00 A")

    assert "Usage" in run(path, "/snooze")
    assert "positive" in run(path, "/snooze 1 0")
    assert "No reminder #1" in run(path, "/snooze 1", chat=222)
    assert db.list_reminders(path, CHAT)[0]["next_run"] == "2026-10-24T07:00:00Z"


def test_cannot_delete_other_chats_reminder(path):
    run(path, "/add 09:00 A", chat=1)
    assert "No reminder #1" in run(path, "/del 1", chat=2)
    assert len(db.list_reminders(path, 1)) == 1


def test_unknown_command_and_bot_suffix(path):
    assert "Unknown command" in run(path, "/nope")
    assert "Saved" in run(path, "/add@MyBot 09:00 A")
