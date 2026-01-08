import aiosqlite
import os

DB_NAME = "music_bot.db"

# Defaults
DEFAULT_VOL = 100
DEFAULT_STEP = int(os.getenv("VOLUME_STEP", "10"))
DEFAULT_LIST = int(os.getenv("QUEUE_LIST_SIZE", "5"))
DEFAULT_EQ = "flat"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                volume INTEGER DEFAULT ?,
                vol_step INTEGER DEFAULT ?,
                list_size INTEGER DEFAULT ?,
                eq_preset TEXT DEFAULT ?
            )
        """, (DEFAULT_VOL, DEFAULT_STEP, DEFAULT_LIST, DEFAULT_EQ))
        await db.commit()

async def get_settings(guild_id: int):
    """Returns a dict of all settings for a guild."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT volume, vol_step, list_size, eq_preset FROM guild_settings WHERE guild_id = ?", 
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "volume": row[0],
                    "vol_step": row[1],
                    "list_size": row[2],
                    "eq_preset": row[3]
                }
            return {
                "volume": DEFAULT_VOL,
                "vol_step": DEFAULT_STEP,
                "list_size": DEFAULT_LIST,
                "eq_preset": DEFAULT_EQ
            }

async def update_setting(guild_id: int, column: str, value):
    if column not in ["volume", "vol_step", "list_size", "eq_preset"]: return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"""
            INSERT INTO guild_settings (guild_id, {column}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {column} = excluded.{column}
        """, (guild_id, value))
        await db.commit()