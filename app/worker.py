import asyncio
import logging
from datetime import datetime

from . import db
from .commands import handle_text
from .schedule import UTC, next_occurrence, to_iso

log = logging.getLogger("worker")

# Simple in-process counters, exposed at /metrics
stats = {"sent": 0, "errors": 0}


def utcnow() -> datetime:
    return datetime.now(UTC)


async def run_due(tg, path: str, tz, now: datetime) -> int:
    """Send every reminder that is due. Failed sends stay in the DB and retry next tick."""
    sent = 0
    for r in db.due_reminders(path, to_iso(now)):
        try:
            await tg.send_message(r["chat_id"], f"Reminder: {r['text']}")
        except Exception as exc:  # never log the exception text: it may contain the bot token
            stats["errors"] += 1
            log.warning("send failed for reminder %s: %s", r["id"], type(exc).__name__)
            continue
        sent += 1
        stats["sent"] += 1
        if r["kind"] == "once":
            db.delete_by_id(path, r["id"])
        else:
            nxt = next_occurrence(r["kind"], r["at_time"], now, tz)
            db.set_next_run(path, r["id"], to_iso(nxt))
    return sent


async def process_update(tg, settings, update: dict, now: datetime) -> None:
    msg = update.get("message")
    if not msg or "text" not in msg:
        return
    chat_id = msg["chat"]["id"]
    text = msg["text"]

    if chat_id not in settings.allowed_chat_ids:
        if text.strip().lower().startswith("/start"):
            await tg.send_message(
                chat_id,
                f"Not authorized. Your chat id is {chat_id}. "
                "Put it in ALLOWED_CHAT_IDS and restart the bot.",
            )
        return

    reply = handle_text(settings.db_path, chat_id, text, now, settings.tz)
    await tg.send_message(chat_id, reply)


async def poll_loop(tg, settings) -> None:
    offset = int(db.get_meta(settings.db_path, "offset") or 0)
    while True:
        try:
            for update in await tg.get_updates(offset):
                offset = update["update_id"] + 1
                await process_update(tg, settings, update, utcnow())
                db.set_meta(settings.db_path, "offset", str(offset))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            stats["errors"] += 1
            log.warning("polling failed: %s", type(exc).__name__)
            await asyncio.sleep(5)


async def scheduler_loop(tg, settings) -> None:
    while True:
        try:
            await run_due(tg, settings.db_path, settings.tz, utcnow())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            stats["errors"] += 1
            log.warning("scheduler tick failed: %s", type(exc).__name__)
        await asyncio.sleep(settings.tick_seconds)
