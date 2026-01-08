import discord
import wavelink
import logging
from discord.ext import commands
from discord import app_commands
from cogs.controls import PlayerControls
from utils import database, helpers

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- /play COMMAND ---
    @app_commands.command(name="play", description="Search and play a song from YouTube/Spotify")
    @app_commands.describe(search="The song name or link")
    async def play(self, interaction: discord.Interaction, search: str):
        # 1. Check Voice State
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)

        # 2. Defer (Tell Discord we are working on it)
        await interaction.response.defer()

        # 3. Connect or Get Player
        try:
            if not interaction.guild.voice_client:
                player: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                
                # Restore Settings from DB
                settings = await database.get_settings(interaction.guild_id)
                await player.set_volume(settings['volume'])
                await helpers.apply_eq(player, settings['eq_preset'])
            else:
                player: wavelink.Player = interaction.guild.voice_client
        except Exception as e:
            print(f"[CONNECTION ERROR]: {e}")
            return await interaction.followup.send("Could not connect to voice channel.")

        # 4. Search and Play (With Error Handling)
        try:
            tracks = await wavelink.Playable.search(search)
            
            if not tracks:
                return await interaction.followup.send(f"❌ No tracks found for: `{search}`")

            track = tracks[0] if isinstance(tracks, list) else tracks

            # Add to Queue
            if isinstance(tracks, wavelink.Playlist):
                for t in tracks: 
                    await player.queue.put_wait(t)
                msg = f"✅ Added playlist **{tracks.name}** ({len(tracks)} songs)"
            else:
                await player.queue.put_wait(track)
                msg = f"✅ Added **{track.title}** to queue."

            # If not playing, start playing
            if not player.playing:
                await player.play(player.queue.get())
                
                # Create Dashboard
                embed = discord.Embed(
                    description=f"Now Playing: **{track.title}**\n{helpers.create_progress_bar(player)}",
                    color=discord.Color.green()
                )
                if track.artwork: 
                    embed.set_thumbnail(url=track.artwork)
                
                settings = await database.get_settings(interaction.guild_id)
                embed.set_footer(text=f"EQ: {settings['eq_preset'].title()} | Vol: {settings['volume']}%")
                
                await interaction.followup.send(embed=embed, view=PlayerControls(player))
            else:
                # Just confirm added to queue
                await interaction.followup.send(msg)

        except wavelink.LavalinkLoadException as e:
            # SPECIFIC LAVALINK ERROR
            print(f"[LAVALINK LOAD ERROR]: {e}")
            await interaction.followup.send(f"❌ Lavalink failed to load this track. It might be region-locked or age-restricted.")
        
        except Exception as e:
            # GENERIC ERROR
            print(f"[CRITICAL MUSIC ERROR]: {e}")
            await interaction.followup.send("❌ An internal error occurred while trying to play the music.")

    # --- /setstep COMMAND ---
    @app_commands.command(name="setstep", description="Set volume change step amount (1-50)")
    async def setstep(self, interaction: discord.Interaction, amount: int):
        if 1 <= amount <= 50:
            await database.update_setting(interaction.guild_id, "vol_step", amount)
            await interaction.response.send_message(f"✅ Volume step set to **{amount}%**.")
        else:
            await interaction.response.send_message("❌ Please choose between 1 and 50.", ephemeral=True)

    # --- /setlist COMMAND ---
    @app_commands.command(name="setlist", description="Set how many songs the list button shows (1-25)")
    async def setlist(self, interaction: discord.Interaction, amount: int):
        if 1 <= amount <= 25:
            await database.update_setting(interaction.guild_id, "list_size", amount)
            await interaction.response.send_message(f"✅ List size set to **{amount}** songs.")
        else:
            await interaction.response.send_message("❌ Please choose between 1 and 25.", ephemeral=True)

    # --- /stop COMMAND ---
    @app_commands.command(name="stop", description="Stop music and disconnect")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 Disconnected.")
        else:
            await interaction.response.send_message("I am not connected.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))