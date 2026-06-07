import asyncio
from sqlalchemy import text
from app.db.session import engine

async def update():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT;"))
            print("Successfully added column bio to users table.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

if __name__ == "__main__":
    asyncio.run(update())
