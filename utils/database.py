import aiosqlite
import os

DB_NAME = "music_bot.db"

# Global Defaults (used if DB is empty)
DEFAULT_VOL = 100
DEFAULT_STEP = int(os.getenv("VOLUME_STEP", "10"))
DEFAULT_LIST = int(os.getenv("QUEUE_LIST_SIZE", "5"))
DEFAULT_EQ = "flat"
DEFAULT_AUTO_LEAVE = 1 if os.getenv("AUTO_LEAVE_ENABLED", "true").lower() in ("true", "1", "yes") else 0
DEFAULT_LEAVE_TIME = int(os.getenv("AUTO_LEAVE_TIME", "300"))

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Create Table if missing
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                volume INTEGER DEFAULT {DEFAULT_VOL},
                vol_step INTEGER DEFAULT {DEFAULT_STEP},
                list_size INTEGER DEFAULT {DEFAULT_LIST},
                eq_preset TEXT DEFAULT '{DEFAULT_EQ}',
                auto_leave INTEGER DEFAULT {DEFAULT_AUTO_LEAVE},
                leave_time INTEGER DEFAULT {DEFAULT_LEAVE_TIME}
            )
        """)
        
        # 2. Migration Check (Add columns if they are missing from an old DB)
        async with db.execute("PRAGMA table_info(guild_settings)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            
        if "auto_leave" not in columns:
            print("Migrating DB: Adding 'auto_leave' column...")
            await db.execute(f"ALTER TABLE guild_settings ADD COLUMN auto_leave INTEGER DEFAULT {DEFAULT_AUTO_LEAVE}")
            
        if "leave_time" not in columns:
            print("Migrating DB: Adding 'leave_time' column...")
            await db.execute(f"ALTER TABLE guild_settings ADD COLUMN leave_time INTEGER DEFAULT {DEFAULT_LEAVE_TIME}")

        await db.commit()

async def get_settings(guild_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT volume, vol_step, list_size, eq_preset, auto_leave, leave_time FROM guild_settings WHERE guild_id = ?", 
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "volume": row[0],
                    "vol_step": row[1],
                    "list_size": row[2],
                    "eq_preset": row[3],
                    "auto_leave": bool(row[4]),
                    "leave_time": row[5]
                }
            return {
                "volume": DEFAULT_VOL,
                "vol_step": DEFAULT_STEP,
                "list_size": DEFAULT_LIST,
                "eq_preset": DEFAULT_EQ,
                "auto_leave": bool(DEFAULT_AUTO_LEAVE),
                "leave_time": DEFAULT_LEAVE_TIME
            }

async def update_setting(guild_id: int, column: str, value):
    valid_cols = ["volume", "vol_step", "list_size", "eq_preset", "auto_leave", "leave_time"]
    if column not in valid_cols: 
        return
        
    async with aiosqlite.connect(DB_NAME) as db:
        # Convert bool to int for SQLite
        if isinstance(value, bool):
            value = 1 if value else 0
            
        await db.execute(f"""
            INSERT INTO guild_settings (guild_id, {column}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {column} = excluded.{column}
        """, (guild_id, value))
        await db.commit()