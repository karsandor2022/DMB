import asyncio
import os
import discord
import wavelink
from discord.ext import commands
from dotenv import load_dotenv
from utils.database import init_db

# Load env vars
load_dotenv()

# --- BOT CLASS DEFINITION ---
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        # Internal prefix required by library, but unused for slash commands
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 1. Initialize Database
        await init_db()
        
        # 2. Load Cogs
        await self.load_extension("cogs.music")
        
        # 3. Connect to Lavalink
        uri = os.getenv("LAVALINK_URL", "http://localhost:2333")
        password = os.getenv("LAVALINK_PASS", "youshallnotpass")
        
        nodes = [wavelink.Node(uri=uri, password=password)]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        
        # --- SYNC SLASH COMMANDS ---
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands globally.")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

        invite = discord.utils.oauth_url(self.user.id, permissions=discord.Permissions(2184563712))
        print(f"\n[INVITE LINK]: {invite}\n")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node Connected: {payload.node.identifier}")

# --- ENTRY POINT ---
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