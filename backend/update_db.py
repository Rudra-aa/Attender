import asyncio
from sqlalchemy import text
from app.db.session import engine

async def update():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE professors ADD COLUMN auto_approve_enrollments BOOLEAN DEFAULT FALSE;"))
            print("Successfully added column auto_approve_enrollments to professors table.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

if __name__ == "__main__":
    asyncio.run(update())
