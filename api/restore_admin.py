import asyncio
import os
import sys

# Add the parent directory to sys.path to allow importing from 'app'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.models.users import User, Organization
from app.core.auth import get_password_hash

async def restore():
    print(f"Connecting to database at {settings.database_url}...")
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create Organization
        print("Creating organization 'CTL Plumbing LLC'...")
        org = Organization(
            name="CTL Plumbing LLC",
            email="corynllc@gmail.com",
            default_county="Dallas"
        )
        session.add(org)
        await session.flush()
        print(f"  + Organization created (id={org.id})")

        # Create Admin User
        print("Creating admin user 'corynllc@gmail.com'...")
        hashed_pwd = get_password_hash("Superhawg-12.0")
        user = User(
            email="corynllc@gmail.com",
            hashed_password=hashed_pwd,
            full_name="Cory Nichols",
            role="admin",
            is_active=True,
            is_admin=True,
            organization_id=org.id
        )
        session.add(user)
        await session.commit()
        print(f"  + Admin user created (id={user.id})")

    await engine.dispose()
    print("\nRestore complete!")

if __name__ == "__main__":
    asyncio.run(restore())
