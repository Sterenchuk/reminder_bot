from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app import db
from app.schedule import UTC

VIENNA = ZoneInfo("Europe/Vienna")
# Fri 23 Oct 2026, 10:00 in Vienna (CEST, UTC+2). DST ends on Sun 25 Oct.
NOW = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)


@pytest.fixture
def path(tmp_path):
    p = str(tmp_path / "test.db")
    db.init_db(p)
    return p
