import asyncio
from sqlalchemy import text
from app.db.session import engine

async def update():
    async with engine.begin() as conn:
        statements = [
            "ALTER TABLE students ADD COLUMN is_face_enrolled BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE students ADD COLUMN is_face_approved BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE students ADD COLUMN enrollment_locked BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE students ADD COLUMN last_approved_at TIMESTAMP WITH TIME ZONE;"
        ]
        
        for stmt in statements:
            try:
                # Savepoint per statement so the transaction doesn't abort
                async with conn.begin_nested():
                    await conn.execute(text(stmt))
                    print(f"Successfully ran: {stmt}")
            except Exception as e:
                print(f"Skipped (already exists): {stmt}")

if __name__ == "__main__":
    asyncio.run(update())
