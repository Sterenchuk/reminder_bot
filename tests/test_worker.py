import asyncio

from app import db
from app.worker import run_due
from tests.conftest import NOW, VIENNA


class FakeTelegram:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    async def send_message(self, chat_id, text):
        if self.fail:
            raise RuntimeError("network down")
        self.sent.append((chat_id, text))


def test_daily_is_sent_and_rescheduled(path):
    db.add_reminder(path, 1, "Vitamins", "daily", "09:00", "2026-10-23T07:00:00Z")
    tg = FakeTelegram()
    assert asyncio.run(run_due(tg, path, VIENNA, NOW)) == 1
    assert tg.sent == [(1, "Reminder: Vitamins")]
    assert db.list_reminders(path, 1)[0]["next_run"] == "2026-10-24T07:00:00Z"


def test_once_is_deleted_after_send(path):
    db.add_reminder(path, 1, "Call", "once", "09:00", "2026-10-23T07:00:00Z")
    asyncio.run(run_due(FakeTelegram(), path, VIENNA, NOW))
    assert db.list_reminders(path, 1) == []


def test_not_due_is_untouched(path):
    db.add_reminder(path, 1, "Later", "daily", "12:00", "2026-10-23T10:00:00Z")
    tg = FakeTelegram()
    assert asyncio.run(run_due(tg, path, VIENNA, NOW)) == 0
    assert tg.sent == []


def test_failed_send_is_retried_later(path):
    db.add_reminder(path, 1, "Call", "once", "09:00", "2026-10-23T07:00:00Z")
    assert asyncio.run(run_due(FakeTelegram(fail=True), path, VIENNA, NOW)) == 0
    assert len(db.list_reminders(path, 1)) == 1  # still there, will retry
