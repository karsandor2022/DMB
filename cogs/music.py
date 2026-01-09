import discord
import wavelink
import asyncio
import os
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
from cogs.controls import PlayerControls
from utils import database, helpers

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Elindítjuk a háttérfolyamatot
        self.player_update_loop.start()

    def cog_unload(self):
        # Ha leáll a bot, állítsuk le a loopot
        self.player_update_loop.cancel()

    # --- 5 MÁSODPERCES FRISSÍTŐ LOOP ---
    @tasks.loop(seconds=6.0)  # 6 másodperc biztonságosabb a rate limit miatt
    async def player_update_loop(self):
        for node in wavelink.Pool.nodes.values():
            for player in node.players.values():
                # Csak akkor frissítsünk, ha játszik és van elmentett üzenet
                if player.playing and hasattr(player, 'last_msg') and player.last_msg:
                    try:
                        # Újrageneráljuk a View-t és az Embed-et
                        # Itt egy trükköt használunk: meghívjuk a PlayerControls update logikáját
                        # Ehhez szükségünk van a PlayerControls osztályra importálva
                        
                        # Mivel nincs "interaction" objektumunk, manuálisan szerkesztjük
                        embed = player.last_msg.embeds[0]
                        bar_text = helpers.create_progress_bar(player)
                        
                        # Megtartjuk az eredeti címet, csak a leírást (progress bar) frissítjük
                        current_title = player.current.title
                        embed.description = f"Now Playing: **{current_title}**\n\n{bar_text}"

                        current_eq = getattr(player, "eq_preset", "flat").title()
                        embed.set_footer(text=f"EQ: {current_eq} | Vol: {player.volume}%")
                        
                        # Megpróbáljuk szerkeszteni az üzenetet
                        await player.last_msg.edit(embed=embed)
                        
                    except Exception as e:
                        # Ha az üzenetet törölték, vagy hiba van, hagyjuk figyelmen kívül
                        pass

    @player_update_loop.before_loop
    async def before_player_update(self):
        # Megvárjuk, amíg a bot elindul
        await self.bot.wait_until_ready()

    async def get_player(self, interaction: discord.Interaction) -> wavelink.Player:
        """Helper to get the player and check voice state."""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ I am not connected to a voice channel.", ephemeral=True)
            return None
        return interaction.guild.voice_client
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        if not player: return

        # RESET FLAG: We have successfully started the "Previous" song, 
        # so we can turn off the "going back" mode.
        if hasattr(player, "is_going_back"):
            player.is_going_back = False

        # ... (Keep your existing UI/Embed code here: Delete old msg, Send new msg) ...
        # 1. Delete old message
        if hasattr(player, 'last_msg') and player.last_msg:
            try:
                await player.last_msg.delete()
            except: pass

        # 2. Get channel
        channel = getattr(player, 'home', None)
        if not channel: return 

        # 3. Build Embed
        track = payload.track
        bar_text = helpers.create_progress_bar(player)
        
        embed = discord.Embed(
            description=f"Now Playing: **{track.title}**\n\n{bar_text}",
            color=discord.Color.green()
        )
        if track.artwork: embed.set_thumbnail(url=track.artwork)

        if not hasattr(player, "eq_preset"):
            try:
                settings = await database.get_settings(player.guild.id)
                player.eq_preset = settings['eq_preset']
            except:
                player.eq_preset = "flat"

        current_eq = player.eq_preset.title()
        embed.set_footer(text=f"EQ: {current_eq} | Vol: {player.volume}%")

        try:
            settings = await database.get_settings(player.guild.id)
            embed.set_footer(text=f"EQ: {settings['eq_preset'].title()} | Vol: {player.volume}%")
        except:
            pass

        # 4. Send
        view = PlayerControls(player)
        player.last_msg = await channel.send(embed=embed, view=view)


    # --- 2. TRACK END (History Saving & Queue Logic) ---
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player: return

        # --- NEW HISTORY LOGIC ---
        # Initialize if missing
        if not hasattr(player, "custom_history"):
            player.custom_history = []
        
        # Only add to history if we are NOT going back.
        # If we skip, 'is_going_back' is False, so it ADDS to history (Correct).
        # If we press Back, 'is_going_back' is True, so we DON'T add (Correct, it goes to Queue).
        if not getattr(player, "is_going_back", False):
            if payload.track.uri:
                player.custom_history.append(payload.track.uri)
        # -------------------------

        # Ignore if replaced (e.g. Skip/Back button was used) 
        # because the command handler (cb_skip/cb_prev) deals with the flow.
        if payload.reason == "replaced":
            return

        # Normal Auto-Play Logic
        if not player.queue.is_empty:
            await player.play(player.queue.get())
            return

        # Auto-Leave Logic
        try:
            guild_settings = await database.get_settings(player.guild.id)
            should_leave = guild_settings.get("auto_leave", True)
            wait_time = guild_settings.get("leave_time", 300)
        except:
            should_leave = True
            wait_time = 300

        if should_leave:
            await asyncio.sleep(wait_time)
            if player.guild.voice_client and not player.playing and player.queue.is_empty:
                if hasattr(player, 'last_msg') and player.last_msg:
                    try: await player.last_msg.delete()
                    except: pass
                await player.disconnect()

    # --- 1. PLAY ---
    @app_commands.command(name="play", description="Search and play a song")
    @app_commands.describe(search="The song name or link")
    async def play(self, interaction: discord.Interaction, search: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)

        await interaction.response.defer()

        if not interaction.guild.voice_client:
            try:
                player: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                player.home = interaction.channel
                player.custom_history = []
                settings = await database.get_settings(interaction.guild_id)
                await player.set_volume(settings['volume'])
                await helpers.apply_eq(player, settings['eq_preset'])
            except Exception as e:
                return await interaction.followup.send("❌ Could not connect to voice channel.")
        else:
            player: wavelink.Player = interaction.guild.voice_client
            player.home = interaction.channel

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

                # Only send the "Added to queue" message if music is already playing
                if player.playing:
                    await interaction.followup.send(msg)
                else:
                    # If we are about to start playing, just acknowledge silently
                    # The on_track_start event will send the big player interface
                    await interaction.followup.send("✅ Loading track...", ephemeral=True)

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

    # --- 2. STOP (Clear Queue + Stop Music + STAY) ---
    @app_commands.command(name="stop", description="Stop music and clear queue (Stays in Voice)")
    async def stop(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            # 1. Clear upcoming songs
            player.queue.clear()
            # 2. Skip current song (force stop since queue is empty)
            await player.skip(force=True)
            await interaction.response.send_message("🛑 Music stopped and queue cleared.")

    # --- 3. LEAVE (Clear Queue + Stop Music + DISCONNECT) ---
    @app_commands.command(name="leave", description="Disconnect the bot completely")
    async def leave(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            # 1. Clear queue
            player.queue.clear()
            # 2. Disconnect (kills audio instantly)
            await player.disconnect()
            await interaction.response.send_message("👋 Disconnected.")

    # --- 4. PAUSE & RESUME ---
    @app_commands.command(name="pause", description="Pause or Resume the music")
    async def pause(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            await player.pause(not player.paused)
            status = "Paused" if player.paused else "Resumed"
            await interaction.response.send_message(f"⏯️ Music **{status}**.")

    # --- 5. SKIP & PREVIOUS ---
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

    # --- 6. VOLUME & MUTE ---
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

    # --- 7. LOOP ---
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

    # --- 8. SEEK ---
    @app_commands.command(name="seek", description="Seek to a specific position (seconds)")
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

    # --- 9. EQ ---
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

    # --- 10. QUEUE ---
    @app_commands.command(name="queue", description="Show the upcoming songs")
    async def queue(self, interaction: discord.Interaction):
        player = await self.get_player(interaction)
        if player:
            queue = player.queue
            if not queue:
                return await interaction.response.send_message("Queue is empty.", ephemeral=True)
            
            desc = ""
            for i, track in enumerate(queue, 1):
                line = f"**{i}.** {track.title} `[{helpers.format_time(track.length)}]`\n"
                if len(desc) + len(line) > 3900: 
                    desc += f"\n*...and {len(queue) - i + 1} more*"
                    break
                desc += line
                
            embed = discord.Embed(title="Current Queue", description=desc, color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
    # ==============================
    #        SETTINGS COMMANDS
    # ==============================
    # Group command: /settings [subcommand]
    settings_group = app_commands.Group(name="settings", description="Configure the music bot settings")

    @settings_group.command(name="view", description="View current settings for this server")
    async def view_settings(self, interaction: discord.Interaction):
        s = await database.get_settings(interaction.guild_id)
        
        embed = discord.Embed(title="⚙️ Server Settings", color=discord.Color.light_grey())
        embed.add_field(name="Auto Leave", value="✅ Enabled" if s['auto_leave'] else "❌ Disabled", inline=True)
        embed.add_field(name="Leave Timer", value=f"{s['leave_time']} seconds", inline=True)
        embed.add_field(name="Volume Step", value=f"{s['vol_step']}%", inline=True)
        embed.add_field(name="Default List Size", value=f"{s['list_size']} songs", inline=True)
        embed.add_field(name="Default EQ", value=f"{s['eq_preset'].title()}", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @settings_group.command(name="auto_leave", description="Enable or Disable auto-disconnecting")
    @app_commands.choices(enabled=[
        app_commands.Choice(name="True (Enable)", value=1),
        app_commands.Choice(name="False (Disable)", value=0)
    ])
    async def set_auto_leave(self, interaction: discord.Interaction, enabled: app_commands.Choice[int]):
        is_enabled = bool(enabled.value)
        await database.update_setting(interaction.guild_id, "auto_leave", is_enabled)
        status = "Enabled" if is_enabled else "Disabled"
        await interaction.response.send_message(f"✅ Auto Leave is now **{status}**.")

    @settings_group.command(name="leave_timer", description="Seconds to wait before leaving (10 - 3600)")
    async def set_leave_timer(self, interaction: discord.Interaction, seconds: int):
        if 10 <= seconds <= 3600:
            await database.update_setting(interaction.guild_id, "leave_time", seconds)
            await interaction.response.send_message(f"✅ Auto Leave timer set to **{seconds} seconds**.")
        else:
            await interaction.response.send_message("❌ Time must be between 10 and 3600 seconds.", ephemeral=True)

    @settings_group.command(name="volume_step", description="How much volume changes per click (1-50)")
    async def set_vol_step(self, interaction: discord.Interaction, amount: int):
        if 1 <= amount <= 50:
            await database.update_setting(interaction.guild_id, "vol_step", amount)
            await interaction.response.send_message(f"✅ Volume step set to **{amount}%**.")
        else:
            await interaction.response.send_message("❌ Step must be between 1 and 50.", ephemeral=True)

    @settings_group.command(name="list_size", description="Set default number of songs shown in queue (1-25)")
    async def set_list_size(self, interaction: discord.Interaction, amount: int):
        if 1 <= amount <= 25:
            await database.update_setting(interaction.guild_id, "list_size", amount)
            await interaction.response.send_message(f"✅ Default list size set to **{amount} songs**.")
        else:
            await interaction.response.send_message("❌ Please choose between 1 and 25.", ephemeral=True)

    @settings_group.command(name="default_eq", description="Set the default EQ loaded when bot joins")
    @app_commands.choices(preset=[
        app_commands.Choice(name="Flat (Normal)", value="flat"),
        app_commands.Choice(name="Bass Boost", value="bass"),
        app_commands.Choice(name="Treble Boost", value="treble"),
        app_commands.Choice(name="Metal", value="metal"),
    ])
    async def set_default_eq(self, interaction: discord.Interaction, preset: app_commands.Choice[str]):
        await database.update_setting(interaction.guild_id, "eq_preset", preset.value)
        await interaction.response.send_message(f"✅ Default EQ set to **{preset.name}**.")

    # --- 11. MANUAL SYNC COMMAND (TEXT BASED) ---
    @commands.command()
    async def sync(self, ctx):
        """Manually syncs slash commands to the current server."""
        try:
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Successfully synced {len(synced)} commands to this server!")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {e}")

async def setup(bot):
    await bot.add_cog(Music(bot))