import discord
import wavelink
import os
from discord.ui import Button, View, Select
from utils import database, helpers

SEEK_SEC = int(os.getenv("SEEK_SECONDS", "15"))

class EQSelect(Select):
    def __init__(self, player):
        options = [
            discord.SelectOption(label="Flat (Normal)", value="flat"),
            discord.SelectOption(label="Bass Boost", value="bass"),
            discord.SelectOption(label="Treble Boost", value="treble"),
            discord.SelectOption(label="Metal", value="metal"),
        ]
        super().__init__(placeholder="Select EQ Preset...", min_values=1, max_values=1, options=options)
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        # FIX: Defer immediately to prevent "Interaction Failed"
        await interaction.response.defer()
        
        val = self.values[0]
        try:
            await helpers.apply_eq(self.player, val)
            await database.update_setting(interaction.guild_id, "eq_preset", val)
            if self.view:
                await self.view.update_embed(interaction)
        except Exception as e:
            print(f"EQ Error: {e}")

class ShortListView(View):
    def __init__(self, queue):
        super().__init__(timeout=180)
        self.queue = queue

    @discord.ui.button(label="Show Full List", style=discord.ButtonStyle.primary)
    async def show_full(self, interaction: discord.Interaction, button: Button):
        # Generate the full text
        full_text = ""
        for i, t in enumerate(self.queue, 1):
            line = f"{i}. {t.title} [{helpers.format_time(t.length)}]\n"
            if len(full_text) + len(line) > 3500:
                full_text += "\n... [Truncated due to Discord limit]"
                break
            full_text += line
        
        full_embed = discord.Embed(title="Full Queue", description=full_text, color=discord.Color.blue())
        
        # FIX: view=None removes the "Close List" button.
        # Users can use the blue "Dismiss message" text provided by Discord.
        await interaction.response.send_message(embed=full_embed, ephemeral=True, view=None)

class PlayerControls(View):
    def __init__(self, player: wavelink.Player, show_eq=False):
        super().__init__(timeout=None)
        self.player = player
        self.show_eq = show_eq
        self.render_buttons()

    def render_buttons(self):
        self.clear_items()
        
        # ROW 0: Prev, Play/Pause, Stop, Skip, Loop
        self.add_item(self.make_btn("⏮️", "prev", row=0))
        
        pp_emoji = "▶️" if self.player.paused else "⏸️"
        pp_style = discord.ButtonStyle.green if self.player.paused else discord.ButtonStyle.red
        self.add_item(self.make_btn(pp_emoji, "pp", style=pp_style, row=0))

        self.add_item(self.make_btn("⏹️", "stop",  row=0))
        self.add_item(self.make_btn("⏭️", "skip", row=0))

        is_looping = self.player.queue.mode == wavelink.QueueMode.loop
        loop_style = discord.ButtonStyle.green if is_looping else discord.ButtonStyle.secondary
        loop_lbl = "🔂" if is_looping else "🔁"
        self.add_item(self.make_btn(loop_lbl, "loop", style=loop_style, row=0))

        # ROW 1: RW, FF, EQ, List, Mute
        self.add_item(self.make_btn(f"⏪ -{SEEK_SEC}s", "rw", row=1))
        self.add_item(self.make_btn(f"+{SEEK_SEC}s ⏩", "ff", row=1))
        
        eq_style = discord.ButtonStyle.primary if self.show_eq else discord.ButtonStyle.secondary
        self.add_item(self.make_btn("🎚️ EQ", "eq", style=eq_style, row=1))
        
        self.add_item(self.make_btn("📜 List", "list", style=discord.ButtonStyle.blurple, row=1))


        # ROW 2: Vol Down, Vol Up
        self.add_item(self.make_btn("🔊 Volume Up ", "vup", row=2))
        mute_icon = "🔊" if self.player.volume > 0 else "🔇"
        self.add_item(self.make_btn(mute_icon, "mute", row=2))
        self.add_item(self.make_btn("🔉 Volume Down ", "vdown", row=2))

        # EQ Dropdown
        if self.show_eq:
            self.add_item(EQSelect(self.player))

    def make_btn(self, label, cb_id, style=discord.ButtonStyle.secondary, row=0):
        btn = Button(style=style, row=row)
        if len(label) <= 2: btn.emoji = label
        else: btn.label = label
        btn.callback = getattr(self, f"cb_{cb_id}")
        return btn

    async def update_embed(self, interaction: discord.Interaction):
        self.render_buttons()
        
        # 1. Determine which message to update
        msg = interaction.message
        if not msg and hasattr(self.player, 'last_msg'):
            msg = self.player.last_msg
            
        if not msg: return

        try:
            if msg.embeds:
                embed = msg.embeds[0]
                
                # Update Bar
                if self.player.current:
                    bar = helpers.create_progress_bar(self.player)
                    embed.description = f"Now Playing: **{self.player.current.title}**\n\n{bar}"

                current_eq = getattr(self.player, "eq_preset", "flat").title()
                embed.set_footer(text=f"EQ: {current_eq} | Vol: {self.player.volume}%")
                
                # Update Footer
                try:
                    settings = await database.get_settings(interaction.guild_id)
                    embed.set_footer(text=f"EQ: {settings['eq_preset'].title()} | Vol: {self.player.volume}%")
                except: pass
                
                # 2. SMART EDIT LOGIC
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                    # Note: edit_message doesn't return the msg object easily, 
                    # but usually interaction.message updates automatically.
                else:
                    new_msg = await msg.edit(embed=embed, view=self)
                    self.player.last_msg = new_msg

        except Exception as e:
            print(f"Update Embed Error: {e}")

    # --- CALLBACKS (Make sure they call update_embed) ---
    async def cb_pp(self, interaction):
        await self.player.pause(not self.player.paused)
        await self.update_embed(interaction)

    async def cb_rw(self, interaction):
        # Seek Backwards
        new_pos = max(0, self.player.position - (SEEK_SEC * 1000))
        await self.player.seek(new_pos)
        await self.update_embed(interaction)

    async def cb_ff(self, interaction):
        # Seek Forwards
        if self.player.current:
            new_pos = min(self.player.current.length, self.player.position + (SEEK_SEC * 1000))
            await self.player.seek(new_pos)
        await self.update_embed(interaction)

    async def cb_vdown(self, interaction):
        settings = await database.get_settings(interaction.guild_id)
        step = settings['vol_step']
        new_vol = max(0, self.player.volume - step)
        await self.player.set_volume(new_vol)
        await database.update_setting(interaction.guild_id, "volume", new_vol)
        await self.update_embed(interaction)

    async def cb_vup(self, interaction):
        settings = await database.get_settings(interaction.guild_id)
        step = settings['vol_step']
        new_vol = min(100, self.player.volume + step)
        await self.player.set_volume(new_vol)
        await database.update_setting(interaction.guild_id, "volume", new_vol)
        await self.update_embed(interaction)

    async def cb_prev(self, interaction):
        # 1. Double Click Logic (Restart if > 10s)
        if self.player.position > 10000:
            await self.player.seek(0)
            await self.update_embed(interaction)
            return

        # 2. History Logic
        if hasattr(self.player, "custom_history") and len(self.player.custom_history) >= 1:
            try:
                # A. Set Flag (Prevents saving to history while going back)
                self.player.is_going_back = True

                # B. Get the Previous Song URI
                prev_uri = self.player.custom_history.pop()

                # C. Handle the Current Song (Put it back to Front of Queue)
                if self.player.current:
                    # Search again to get a fresh track object
                    current_tracks = await wavelink.Playable.search(self.player.current.uri)
                    if current_tracks:
                        curr_track = current_tracks[0] if isinstance(current_tracks, list) else current_tracks
                        
                        # --- FIX: ADD TO FRONT OF QUEUE ---
                        # Since .insert() is missing, we use this workaround:
                        # 1. Copy current queue to a list
                        existing_queue = list(self.player.queue)
                        # 2. Clear the actual queue
                        self.player.queue.clear()
                        # 3. Add the song we just left to the START of our list
                        existing_queue.insert(0, curr_track)
                        # 4. Put everything back into the queue
                        for t in existing_queue:
                            await self.player.queue.put_wait(t)
                        # ----------------------------------

                # D. Play Previous
                prev_tracks = await wavelink.Playable.search(prev_uri)
                if prev_tracks:
                    prev_track = prev_tracks[0] if isinstance(prev_tracks, list) else prev_tracks
                    await self.player.play(prev_track)
                    await interaction.response.defer()
                else:
                    await interaction.followup.send("❌ Could not load previous song.", ephemeral=True)
                    self.player.is_going_back = False 
                
            except Exception as e:
                print(f"Prev Error: {e}")
                await interaction.followup.send("❌ Error going back.", ephemeral=True)
                self.player.is_going_back = False
        else:
            await interaction.response.send_message("❌ No history available.", ephemeral=True)

    async def cb_stop(self, interaction):
        await self.player.disconnect()
        await interaction.response.send_message("🛑 Disconnected.", ephemeral=True)

    async def cb_skip(self, interaction):
        await self.player.skip(force=True)
        await interaction.response.send_message("Skipped.", ephemeral=True)

    async def cb_loop(self, interaction):
        if self.player.queue.mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            await interaction.response.send_message("🔂 Loop Enabled", ephemeral=True)
        else:
            self.player.queue.mode = wavelink.QueueMode.normal
            await interaction.response.send_message("🔁 Loop Disabled", ephemeral=True)
        await self.refresh(interaction)

    async def cb_eq(self, interaction):
        self.show_eq = not self.show_eq
        await self.update_embed(interaction)

    async def cb_list(self, interaction: discord.Interaction):
        queue = self.player.queue
        if not queue: 
            return await interaction.response.send_message("Queue is empty.", ephemeral=True)
        
        # Get settings for list size
        try:
            settings = await database.get_settings(interaction.guild_id)
            list_size = settings['list_size']
        except:
            list_size = 5

        # Build the Short List (Up Next)
        desc = ""
        for i, track in enumerate(queue[:list_size], 1):
            desc += f"**{i}.** {track.title} `[{helpers.format_time(track.length)}]`\n"
        
        remaining = len(queue) - list_size
        if remaining > 0: 
            desc += f"\n*...and {remaining} more*"
        
        embed = discord.Embed(title=f"Up Next (Showing {list_size})", description=desc, color=discord.Color.blue())
        
        # Logic: If there are hidden songs, use the Button View. If not, no buttons.
        if remaining > 0:
            # We pass the FULL queue to the view so it can display it
            await interaction.response.send_message(embed=embed, ephemeral=True, view=ShortListView(queue))
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cb_mute(self, interaction):
        if self.player.volume > 0:
            self.player.last_vol = self.player.volume
            await self.player.set_volume(0)
        else:
            vol = getattr(self.player, 'last_vol', 50)
            await self.player.set_volume(vol)
        await self.refresh(interaction)

