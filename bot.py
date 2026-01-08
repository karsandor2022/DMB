import discord
import wavelink
import os
from discord.ext import commands
from utils.database import init_db

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 1. Initialize Database
        await init_db()
        
        # 2. Load Cogs
        await self.load_extension("cogs.music")
        # Note: controls is imported by music, so we don't need to load it as an ext if it has no commands
        
        # 3. Connect to Lavalink
        nodes = [wavelink.Node(
            uri=os.getenv("LAVALINK_URI", "http://localhost:2333"),
            password=os.getenv("LAVALINK_PASS", "youshallnotpass")
        )]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        invite = discord.utils.oauth_url(self.user.id, permissions=discord.Permissions(8))
        print(f"\n[INVITE LINK]: {invite}\n")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node Connected: {payload.node.identifier}")