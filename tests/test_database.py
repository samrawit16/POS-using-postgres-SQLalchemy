"""The real get_db dependency (other tests replace it with a test-database version)."""
import pytest
from sqlalchemy import text

from app.database import get_db


def test_get_db_yields_a_working_session_and_closes_it():
    gen = get_db()
    db = next(gen)
    assert db.execute(text("select 1")).scalar() == 1
    with pytest.raises(StopIteration):
        next(gen)  # generator finishes -> session closed in `finally`


def test_get_db_rolls_back_and_reraises_on_error():
    gen = get_db()
    db = next(gen)
    rolled_back = []
    original = db.rollback
    db.rollback = lambda: (rolled_back.append(True), original())[1]
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert rolled_back == [True]
