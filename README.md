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

## Run in Kubernetes
The manifests are in `k8s/`. They create a one-replica Deployment, a PVC mounted
at `/data`, a ConfigMap, and an internal Service. Create the bot token Secret
outside Git (for example, locally with `kubectl create secret generic
reminder-secret --from-literal=BOT_TOKEN='your-token'`), then apply the manifests:

    kubectl apply -f k8s/

For a local kind cluster, build and load the image before applying the manifests:

    docker build -t reminder-bot:latest .
    kind load docker-image reminder-bot:latest
    kubectl apply -f k8s/
    kubectl port-forward service/reminder-bot 8000:8000

The API is then available at `http://localhost:8000`. The cluster needs a default
StorageClass or another provisioner for the PVC to become bound.

The GitHub Actions workflow deploys successful pushes to `main`. Configure the
`DOCKERHUB_USERNAME` Actions variable and the `DOCKERHUB_TOKEN`, `BOT_TOKEN`, and
`KUBECONFIG` Actions secrets. The kubeconfig must point to a Kubernetes API
reachable by the GitHub runner; a private k3s API requires a self-hosted runner
on a network that can reach it. Use a kubeconfig with only the permissions needed
to manage this application's resources.

## Bot setup
1. Talk to @BotFather, send /newbot, copy the token into .env as BOT_TOKEN.
2. Start the app, send /start to your bot. It replies with your chat id.
3. Put the id in ALLOWED_CHAT_IDS, restart. Send /help.

## Endpoints
GET /health (liveness), GET /ready (DB check), GET /metrics (Prometheus text)

## Important
Run exactly ONE instance: two pollers on the same token fight each other (Telegram returns 409),
and SQLite is a single-writer file.
