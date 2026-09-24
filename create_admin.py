"""Create the first admin account (there is deliberately no public sign-up).

    python create_admin.py                      # prompts for everything
    python create_admin.py --username alice --email alice@shop.com

The password is always read from a hidden prompt (or the POS_ADMIN_PASSWORD
environment variable for automation) - never from a command-line argument, so it
doesn't end up in shell history or the process list.
"""
import argparse
import getpass
import os
import sys

from pydantic import ValidationError

from app import models  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.repositories.user import user_repository
from app.schemas.user import UserCreate
from app.services.user import create_user


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--username")
    ap.add_argument("--email")
    ap.add_argument("--first-name")
    ap.add_argument("--last-name")
    args = ap.parse_args()

    username = args.username or input("Username: ").strip()
    email = args.email or input("Email: ").strip()
    first = args.first_name or input("First name: ").strip()
    last = args.last_name or input("Last name: ").strip()
    password = os.environ.get("POS_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Password (min 12 chars, letters + digits): ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1

    try:
        data = UserCreate(
            username=username, email=email, password=password,
            first_name=first, last_name=last, role="admin",
        )
    except ValidationError as e:
        for err in e.errors():
            print(f"- {'.'.join(map(str, err['loc']))}: {err['msg']}", file=sys.stderr)
        return 1

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if user_repository.get_by_username(db, data.username) or user_repository.get_by_email(db, data.email):
            print("A user with that username or email already exists.", file=sys.stderr)
            return 1
        user = create_user(db, data)
        print(f"Created admin '{user.username}' (id={user.id}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
