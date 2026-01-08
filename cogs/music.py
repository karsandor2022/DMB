import discord
import wavelink
from discord.ext import commands
from discord import app_commands
from cogs.controls import PlayerControls
from utils import database, helpers
import datetime

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_player(self, interaction: discord.Interaction) -> wavelink.Player:
        """Helper to get the player and check voice state."""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ I am not connected to a voice channel.", ephemeral=True)
            return None
        return interaction.guild.voice_client

    # --- 1. PLAY & STOP ---
    @app_commands.command(name="play", description="Search and play a song from YouTube/Spotify")
    @app_commands.describe(search="The song name or link")
    async def play(self, interaction: discord.Interaction, search: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)

        await interaction.response.defer()

        # Connect if not connected
        if not interaction.guild.voice_client:
            try:
                player: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                # Restore DB settings
                settings = await database.get_settings(interaction.guild_id)
                await player.set_volume(settings['volume'])
                await helpers.apply_eq(player, settings['eq_preset'])
            except Exception as e:
                return await interaction.followup.send("❌ Could not connect to voice channel.")
        else:
            player: wavelink.Player = interaction.guild.voice_client

        # Search
        try:
            tracks = await wavelink.Playable.search(search)
            if not tracks:
                return await interaction.followup.send(f"❌ No tracks found for: `{search}`")

            track = tracks[0] if isinstance(tracks, list) else tracks

            if isinstance(tracks, wavelink.Playlist):
                for t in tracks: await player.queue.put_wait(t)
                msg = f"✅ Added playlist **{tracks.name}** ({len(tracks)} songs)"
            else:
                await player.queue.put_wait(track)
                msg = f"✅ Added **{track.title}** to queue."

            if not player.playing:
                await player.play(player.queue.get())
                
                embed = discord.Embed(
                    description=f"Now Playing: **{track.title}**\n{helpers.create_progress_bar(player)}",
                    color=discord.Color.green()
                )
                if track.artwork: embed.set_thumbnail(url=track.artwork)
                
                settings = await database.get_settings(interaction.guild_id)
                embed.set_footer(text=f"EQ: {settings['eq_preset'].title()} | Vol: {settings['volume']}%")
                
                await interaction.followup.send(embed=embed, view=PlayerControls(player))
            else:
                await interaction.followup.send(msg)

        except Exception as e:
            await interaction.followup.send(f"❌ Error playing track: {e}")

    @app_commands.command(name="stop", description="Stop music and disconnect")
    async def stop(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            await player.disconnect()
            await interaction.response.send_message("👋 Disconnected.")

    # --- 2. PAUSE & RESUME ---
    @app_commands.command(name="pause", description="Pause or Resume the music")
    async def pause(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            await player.pause(not player.paused)
            status = "Paused" if player.paused else "Resumed"
            await interaction.response.send_message(f"⏯️ Music **{status}**.")

    # --- 3. SKIP & PREVIOUS ---
    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            await player.skip(force=True)
            await interaction.response.send_message("⏭️ Skipped song.")

    @app_commands.command(name="previous", description="Play the previous song")
    async def previous(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            try:
                if player.queue.history:
                    await player.play(player.queue.history[-1])
                    await interaction.response.send_message("⏮️ Replaying previous track.")
                else:
                    await interaction.response.send_message("❌ No history available.", ephemeral=True)
            except:
                await interaction.response.send_message("❌ Cannot go back.", ephemeral=True)

    # --- 4. VOLUME & MUTE ---
    @app_commands.command(name="volume", description="Set volume (0-100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        player = await self.get_player(interaction)
        if player:
            vol = max(0, min(100, level))
            await player.set_volume(vol)
            await database.update_setting(interaction.guild_id, "volume", vol)
            await interaction.response.send_message(f"🔊 Volume set to **{vol}%**.")

    @app_commands.command(name="mute", description="Toggle Mute")
    async def mute(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            if player.volume > 0:
                player.last_vol = player.volume
                await player.set_volume(0)
                await interaction.response.send_message("🔇 Muted.")
            else:
                vol = getattr(player, 'last_vol', 50)
                await player.set_volume(vol)
                await interaction.response.send_message("🔊 Unmuted.")

    # --- 5. LOOP ---
    @app_commands.command(name="loop", description="Toggle looping the current song")
    async def loop(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            if player.queue.mode == wavelink.QueueMode.normal:
                player.queue.mode = wavelink.QueueMode.loop
                await interaction.response.send_message("🔂 Loop **Enabled**.")
            else:
                player.queue.mode = wavelink.QueueMode.normal
                await interaction.response.send_message("🔁 Loop **Disabled**.")

    # --- 6. SEEK ---
    @app_commands.command(name="seek", description="Seek to a specific position (e.g., 0 for restart)")
    @app_commands.describe(seconds="Time in seconds to seek to")
    async def seek(self, interaction: discord.Interaction, seconds: int):
        player = await self.get_player(interaction)
        if player:
            position = seconds * 1000
            if position > player.current.length:
                 return await interaction.response.send_message("❌ Seek time is longer than the song.", ephemeral=True)
            await player.seek(position)
            await interaction.response.send_message(f"⏩ Seeked to **{seconds}s**.")

    @app_commands.command(name="rewind", description="Rewind by 15 seconds")
    async def rewind(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            new_pos = max(0, player.position - 15000)
            await player.seek(new_pos)
            await interaction.response.send_message("⏪ Rewound 15s.")

    @app_commands.command(name="forward", description="Fast forward by 15 seconds")
    async def forward(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            new_pos = min(player.current.length, player.position + 15000)
            await player.seek(new_pos)
            await interaction.response.send_message("⏩ Fast-forwarded 15s.")

    # --- 7. EQ ---
    @app_commands.command(name="eq", description="Set Equalizer Preset")
    @app_commands.choices(preset=[
        app_commands.Choice(name="Flat (Normal)", value="flat"),
        app_commands.Choice(name="Bass Boost", value="bass"),
        app_commands.Choice(name="Treble Boost", value="treble"),
        app_commands.Choice(name="Metal", value="metal"),
    ])
    async def eq(self, interaction: discord.Interaction, preset: app_commands.Choice[str]):
        player = await self.get_player(interaction)
        if player:
            await helpers.apply_eq(player, preset.value)
            await database.update_setting(interaction.guild_id, "eq_preset", preset.value)
            await interaction.response.send_message(f"🎚️ EQ set to **{preset.name}**.")

    # --- 8. QUEUE (LIST) ---
    @app_commands.command(name="queue", description="Show the upcoming songs")
    async def queue(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            queue = player.queue
            if not queue:
                return await interaction.response.send_message("Queue is empty.", ephemeral=True)
            
            # Get full list formatted
            desc = ""
            for i, track in enumerate(queue, 1):
                line = f"**{i}.** {track.title} `[{helpers.format_time(track.length)}]`\n"
                if len(desc) + len(line) > 3900: # Discord limit safety
                    desc += f"\n*...and {len(queue) - i + 1} more*"
                    break
                desc += line
                
            embed = discord.Embed(title="Current Queue", description=desc, color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)

    # --- 9. MANUAL SYNC COMMAND (TEXT BASED) ---
    # Type "!sync" in chat to run this.
    @commands.command()
    async def sync(self, ctx):
        """Manually syncs slash commands to the current server."""
        try:
            # Sync to current guild only (Instant update)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Successfully synced {len(synced)} commands to this server!")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {e}")
            
async def setup(bot):
    await bot.add_cog(Music(bot))