# reminder-bot

FastAPI + SQLite + Telegram long polling. Reminders: one-shot, daily, Mon-Fri.
Use `/snooze ID [minutes]` to move a reminder's next run; the default is 10 minutes.

## Run locally
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    pytest
    cp .env.example .env        # fill BOT_TOKEN
    set -a && . ./.env && set +a
    uvicorn app.main:app --reload

## Run in Docker
    docker compose up --build -d
    docker compose logs -f

## Bot setup
1. Talk to @BotFather, send /newbot, copy the token into .env as BOT_TOKEN.
2. Start the app, send /start to your bot. It replies with your chat id.
3. Put the id in ALLOWED_CHAT_IDS, restart. Send /help.

## Endpoints
GET /health (liveness), GET /ready (DB check), GET /metrics (Prometheus text)

## Important
Run exactly ONE instance: two pollers on the same token fight each other (Telegram returns 409),
and SQLite is a single-writer file.
