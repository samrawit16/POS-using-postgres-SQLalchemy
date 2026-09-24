"""The bootstrap script for the first admin (there is deliberately no public sign-up)."""
import sys

import pytest
from sqlalchemy import select

import create_admin
from app.models.user import User
from tests.conftest import STRONG_PASSWORD, do_login


@pytest.fixture()
def script(monkeypatch, session_factory, engine):
    """Point the script at the test database and clear anything ambient."""
    monkeypatch.setattr(create_admin, "SessionLocal", session_factory)
    monkeypatch.setattr(create_admin, "engine", engine)
    monkeypatch.delenv("POS_ADMIN_PASSWORD", raising=False)

    def run(*argv, password=STRONG_PASSWORD, confirm=None, env_password=None):
        monkeypatch.setattr(sys, "argv", ["create_admin.py", *argv])
        answers = iter([password, password if confirm is None else confirm])
        monkeypatch.setattr(create_admin.getpass, "getpass", lambda prompt="": next(answers))
        if env_password is not None:
            monkeypatch.setenv("POS_ADMIN_PASSWORD", env_password)
        return create_admin.main()

    return run


ARGS = ("--username", "Boss", "--email", "boss@example.com", "--first-name", "Big", "--last-name", "Boss")


def test_creates_admin_who_can_log_in(script, client, session_factory, capsys):
    assert script(*ARGS) == 0
    assert "Created admin 'boss'" in capsys.readouterr().out
    with session_factory() as db:
        u = db.scalars(select(User)).one()
    assert u.role == "admin" and u.is_active and u.password_hash.startswith("$argon2id$")
    assert do_login(client, "boss", STRONG_PASSWORD).status_code == 200
    me = client.get("/auth/me", headers={"Authorization": "Bearer " + do_login(client, "boss", STRONG_PASSWORD).json()["access_token"]})
    assert me.json()["role"] == "admin"


def test_password_can_come_from_environment_for_automation(script, client):
    assert script(*ARGS, env_password="Aut0mated-Passw0rd!") == 0
    assert do_login(client, "boss", "Aut0mated-Passw0rd!").status_code == 200


def test_rejects_mismatched_confirmation(script, session_factory, capsys):
    assert script(*ARGS, confirm="different-Passw0rd!") == 1
    assert "do not match" in capsys.readouterr().err
    with session_factory() as db:
        assert db.scalars(select(User)).first() is None


@pytest.mark.parametrize("bad", ["short1", "nodigitsatallhere", "1234567890123"])
def test_rejects_weak_password(script, session_factory, capsys, bad):
    assert script(*ARGS, password=bad) == 1
    assert "password" in capsys.readouterr().err
    with session_factory() as db:
        assert db.scalars(select(User)).first() is None


def test_refuses_duplicate(script, capsys):
    assert script(*ARGS) == 0
    assert script(*ARGS) == 1
    assert "already exists" in capsys.readouterr().err


def test_rejects_invalid_email(script, capsys):
    assert script("--username", "boss", "--email", "nope", "--first-name", "a", "--last-name", "b") == 1
    assert "email" in capsys.readouterr().err
