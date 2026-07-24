"""Bootstrap a landlord/platform-admin account.

There is no self-service signup for platform admins by design — this identity
space controls tenant ops (suspend/activate, cross-tenant visibility), so
provisioning is a deliberate, out-of-band action, not an API endpoint.

Usage (from apps/api):
    python scripts/create_platform_admin.py you@cios.ai --name "Your Name" --role admin
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

sys.path.insert(0, ".")

from sqlalchemy import select  # noqa: E402

from cios.core.database import async_session_factory  # noqa: E402
from cios.core.security import hash_password  # noqa: E402
from cios.models.tenant import PlatformAdmin  # noqa: E402


async def main(email: str, full_name: str, role: str) -> None:
    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        raise SystemExit(1)
    if password != getpass.getpass("Confirm password: "):
        print("Passwords did not match.", file=sys.stderr)
        raise SystemExit(1)

    async with async_session_factory() as db:
        existing = (
            await db.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
        ).scalar_one_or_none()
        if existing:
            print(f"Platform admin '{email}' already exists (id={existing.id}).", file=sys.stderr)
            raise SystemExit(1)

        admin = PlatformAdmin(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"Created platform admin '{admin.email}' (id={admin.id}, role={admin.role}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("--name", required=True, dest="full_name")
    parser.add_argument("--role", choices=("support", "admin"), default="support")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.full_name, args.role))
