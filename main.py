import asyncio
import os
import discord
from dotenv import load_dotenv
from bot import MusicBot

# Load env vars (works for both local .env and Pelican variables)
load_dotenv()

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("CRITICAL ERROR: BOT_TOKEN is missing.")
        return

    bot = MusicBot()
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass