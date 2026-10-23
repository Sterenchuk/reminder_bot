from fastapi.testclient import TestClient

from app.main import app


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("ENABLE_BOT", "0")
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    return TestClient(app)


def test_health(monkeypatch, tmp_path):
    with make_client(monkeypatch, tmp_path) as c:
        r = c.get("/health")
        assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_ready(monkeypatch, tmp_path):
    with make_client(monkeypatch, tmp_path) as c:
        assert c.get("/ready").status_code == 200


def test_metrics(monkeypatch, tmp_path):
    with make_client(monkeypatch, tmp_path) as c:
        body = c.get("/metrics").text
        assert "reminderbot_reminders_active 0" in body
        assert "reminderbot_messages_sent_total" in body
