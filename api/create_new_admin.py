import asyncio
import os
import sys

# Add the parent directory to sys.path to allow importing from 'app'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models.users import User, Organization
from app.core.auth import get_password_hash

async def create_admin():
    email = "admin@ctlplumbingllc.com"
    password = "Ux4600-420"
    
    print(f"Connecting to database...")
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get the organization
        result = await session.execute(select(Organization).where(Organization.name == "CTL Plumbing LLC"))
        org = result.scalar_one_or_none()
        
        org_id = org.id if org else None
        if not org:
            print("Warning: 'CTL Plumbing LLC' organization not found. Creating user without org link.")

        # Create/Update the Admin User
        print(f"Creating/Updating admin user '{email}'...")
        hashed_pwd = get_password_hash(password)
        
        # Check if user already exists
        exist_result = await session.execute(select(User).where(User.email == email))
        existing_user = exist_result.scalar_one_or_none()
        
        if existing_user:
            print(f"User '{email}' already exists. Updating password...")
            existing_user.hashed_password = hashed_pwd
            existing_user.is_admin = True
            existing_user.is_active = True
        else:
            user = User(
                email=email,
                hashed_password=hashed_pwd,
                full_name="System Admin",
                role="admin",
                is_active=True,
                is_admin=True,
                organization_id=org_id
            )
            session.add(user)
        
        await session.commit()
        print(f"Success: Admin user '{email}' is ready.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_admin())
