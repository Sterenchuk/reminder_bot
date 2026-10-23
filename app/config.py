import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    bot_token: str
    allowed_chat_ids: frozenset
    db_path: str
    tz: ZoneInfo
    tick_seconds: float
    enable_bot: bool


def get_settings() -> Settings:
    """Read settings from environment variables (12-factor style)."""
    ids = os.getenv("ALLOWED_CHAT_IDS", "")
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        allowed_chat_ids=frozenset(int(x) for x in ids.split(",") if x.strip()),
        db_path=os.getenv("DB_PATH", "data/reminders.db"),
        tz=ZoneInfo(os.getenv("TIMEZONE", "Europe/Vienna")),
        tick_seconds=float(os.getenv("TICK_SECONDS", "15")),
        enable_bot=os.getenv("ENABLE_BOT", "1") == "1",
    )
