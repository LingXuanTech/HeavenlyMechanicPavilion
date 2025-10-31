#!/usr/bin/env python3
"""Script to create an initial admin user."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select

from app.config import get_settings
from app.db.models import User, UserRole
from app.db.session import DatabaseManager
from app.security import hash_password


async def create_admin_user(
    username: str = "admin",
    email: str = "admin@tradingagents.local",
    password: str = "admin123",
    full_name: str = "System Administrator",
):
    """Create an admin user.

    Args:
        username: Admin username
        email: Admin email
        password: Admin password
        full_name: Admin full name
    """
    settings = get_settings()

    db_manager = DatabaseManager(settings.database_url, echo=settings.database_echo)

    async with db_manager.session_factory() as session:
        statement = select(User).where(User.username == username)
        result = await session.execute(statement)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User '{username}' already exists!")
            return

        admin_user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
        )

        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        print("Admin user created successfully!")
        print(f"Username: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print(f"Role: {admin_user.role.value}")
        print(f"ID: {admin_user.id}")

    await db_manager.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--email", default="admin@tradingagents.local", help="Admin email")
    parser.add_argument("--password", default="admin123", help="Admin password")
    parser.add_argument("--full-name", default="System Administrator", help="Admin full name")

    args = parser.parse_args()

    asyncio.run(
        create_admin_user(
            username=args.username,
            email=args.email,
            password=args.password,
            full_name=args.full_name,
        )
    )
