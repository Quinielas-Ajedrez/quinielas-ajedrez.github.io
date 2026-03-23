#!/usr/bin/env python3
"""
Create a user (for bootstrapping).
Usage: uv run python -m backend.create_user <name> <username> <password> [--admin] [--super-admin]
  --admin       : regular admin (tournaments, games, rounds)
  --super-admin : super-admin (can also assign admin to others)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, init_db
from backend.deps import hash_password
from backend.repository import save_user
from backend.models import User


def main() -> None:
    if "--promote-super-admin" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python -m backend.create_user --promote-super-admin <username>")
            sys.exit(1)
    elif len(sys.argv) < 4:
        print("Usage: python -m backend.create_user <name> <username> <password> [--admin] [--super-admin]")
        print("       python -m backend.create_user --promote-super-admin <username>  # upgrade existing user")
        sys.exit(1)

    init_db()

    if "--promote-super-admin" in sys.argv:
        idx = sys.argv.index("--promote-super-admin")
        if idx + 1 >= len(sys.argv):
            print("Usage: python -m backend.create_user --promote-super-admin <username>")
            sys.exit(1)
        username = sys.argv[idx + 1]
        with SessionLocal() as session:
            from backend.repository import get_user_by_username

            u = get_user_by_username(session, username)
            if u is None:
                print(f"User {username!r} not found")
                sys.exit(1)
            user = save_user(
                session,
                User(
                    id=u.id,
                    name=u.name,
                    username=u.username,
                    password_hash=u.password_hash,
                    is_admin=True,
                    is_super_admin=True,
                ),
            )
            print(f"Promoted {user.username} to super-admin")
        return

    name = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    is_admin = "--admin" in sys.argv or "--super-admin" in sys.argv
    is_super_admin = "--super-admin" in sys.argv

    with SessionLocal() as session:
        from backend.repository import get_user_by_username

        existing = get_user_by_username(session, username)
        if existing:
            if is_super_admin and not existing.is_super_admin:
                user = save_user(
                    session,
                    User(
                        id=existing.id,
                        name=existing.name,
                        username=existing.username,
                        password_hash=existing.password_hash,
                        is_admin=True,
                        is_super_admin=True,
                    ),
                )
                print(f"Upgraded {user.username} to super-admin")
            else:
                print(f"User {username!r} already exists")
            return

        user = save_user(
            session,
            User(
                name=name,
                username=username,
                password_hash=hash_password(password),
                is_admin=is_admin,
                is_super_admin=is_super_admin,
            ),
        )
        roles = []
        if user.is_super_admin:
            roles.append("super-admin")
        elif user.is_admin:
            roles.append("admin")
        print(f"Created user: {user.username} (id={user.id}, roles={', '.join(roles) or 'user'})")


if __name__ == "__main__":
    main()
