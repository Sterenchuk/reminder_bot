import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from . import db
from .config import get_settings
from .telegram import TelegramClient
from .worker import poll_loop, scheduler_loop, stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs full request URLs at INFO, and the Telegram URL contains the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db.init_db(settings.db_path)
    app.state.settings = settings
    tasks, tg = [], None
    if settings.enable_bot and settings.bot_token:
        tg = TelegramClient(settings.bot_token)
        tasks = [
            asyncio.create_task(poll_loop(tg, settings)),
            asyncio.create_task(scheduler_loop(tg, settings)),
        ]
        log.info("bot started")
    else:
        log.warning("bot disabled (no BOT_TOKEN or ENABLE_BOT=0), API only")
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    if tg:
        await tg.aclose()


app = FastAPI(title="reminder-bot", lifespan=lifespan)


@app.get("/health")
def health():
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: the database is usable."""
    try:
        db.count_reminders(app.state.settings.db_path)
    except Exception:
        return JSONResponse({"status": "db unavailable"}, status_code=503)
    return {"status": "ready"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    active = db.count_reminders(app.state.settings.db_path)
    return (
        "# TYPE reminderbot_reminders_active gauge\n"
        f"reminderbot_reminders_active {active}\n"
        "# TYPE reminderbot_messages_sent_total counter\n"
        f"reminderbot_messages_sent_total {stats['sent']}\n"
        "# TYPE reminderbot_errors_total counter\n"
        f"reminderbot_errors_total {stats['errors']}\n"
    )
