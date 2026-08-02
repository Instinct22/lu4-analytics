#!/usr/bin/env python3
"""Seed users from SEED_USERS env (user:pass,user2:pass2) and ensure role permissions."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select

from api.deps import ensure_role_permissions_seeded, hash_password
from config import settings
from database import SessionLocal
from models.user import User


def main() -> None:
    db = SessionLocal()
    try:
        ensure_role_permissions_seeded(db)
        for entry in settings.seed_users.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            username, password = entry.split(":", 1)
            existing = db.scalar(select(User).where(User.username == username))
            if existing:
                if username == "admin" and existing.role == "admin":
                    existing.role = "superadmin"
                    db.commit()
                    print(f"Updated user {username} role to superadmin")
                else:
                    print(f"User {username} already exists, skipping")
                continue
            role = "superadmin" if username == "admin" else "user"
            user = User(
                id=uuid.uuid4(),
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
            )
            db.add(user)
            print(f"Created user: {username} ({role})")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
