import asyncio
from app.core.database import get_db
from app.models.role import Role
from sqlalchemy import select

async def check_roles():
    async for db in get_db():
        result = await db.execute(select(Role))
        roles = result.scalars().all()
        print(f'Total roles in database: {len(roles)}')
        for role in roles:
            print(f'- {role.name}: {role.display_name}')
        break

if __name__ == "__main__":
    asyncio.run(check_roles())