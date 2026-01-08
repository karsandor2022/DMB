import discord
import wavelink
import os
from discord.ui import Button, View, Select
from utils import database, helpers

SEEK_SEC = int(os.getenv("SEEK_SECONDS", "15"))

class EQSelect(Select):
    def __init__(self, player):
        options = [
            discord.SelectOption(label="Flat", value="flat"),
            discord.SelectOption(label="Bass Boost", value="bass"),
            discord.SelectOption(label="Treble", value="treble"),
            discord.SelectOption(label="Metal", value="metal"),
        ]
        super().__init__(placeholder="Select EQ Preset...", min_values=1, max_values=1, options=options)
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        await helpers.apply_eq(self.player, val)
        await database.update_setting(interaction.guild_id, "eq_preset", val)
        await interaction.response.send_message(f"EQ saved as **{val}**", ephemeral=True)

class FullListView(View):
    @discord.ui.button(label="Close List", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()

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
        """Refreshes buttons and the Progress Bar inside the Embed."""
        self.render_buttons()
        
        # Check if the message has an embed to edit
        if not interaction.message.embeds:
            return await interaction.response.edit_message(view=self)
            
        embed = interaction.message.embeds[0]
        
        # 1. Update Title/Description with the Bar
        if self.player.current:
            # Generate the bar using the helper function
            bar_text = helpers.create_progress_bar(self.player)
            embed.description = f"Now Playing: **{self.player.current.title}**\n\n{bar_text}"
            
            # Update Thumbnail if changed (e.g. playlist)
            if self.player.current.artwork:
                embed.set_thumbnail(url=self.player.current.artwork)
        else:
            embed.description = "Nothing is playing."
        
        # 2. Update Footer (Volume / EQ)
        settings = await database.get_settings(interaction.guild_id)
        embed.set_footer(text=f"EQ: {settings['eq_preset'].title()} | Vol: {self.player.volume}%")
        
        await interaction.response.edit_message(embed=embed, view=self)

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
        try:
            if self.player.queue.history:
                await self.player.play(self.player.queue.history[-1])
                await interaction.response.send_message("Replaying previous.", ephemeral=True)
            else: await interaction.response.send_message("No history.", ephemeral=True)
        except: pass

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
        await self.refresh(interaction)

    async def cb_list(self, interaction):
        queue = self.player.queue
        if not queue: return await interaction.response.send_message("Queue is empty.", ephemeral=True)
        
        settings = await database.get_settings(interaction.guild_id)
        list_size = settings['list_size']

        desc = ""
        for i, track in enumerate(queue[:list_size], 1):
            desc += f"**{i}.** {track.title} `[{helpers.format_time(track.length)}]`\n"
        
        remaining = len(queue) - list_size
        if remaining > 0: desc += f"\n*...and {remaining} more*"
        
        embed = discord.Embed(title=f"Up Next (Showing {list_size})", description=desc, color=discord.Color.blue())
        
        view = View()
        if remaining > 0:
            btn_full = Button(label="Show Full List", style=discord.ButtonStyle.primary)
            async def full_list_callback(inter):
                full_text = "\n".join([f"{i}. {t.title}" for i, t in enumerate(queue, 1)])
                if len(full_text) > 4000: full_text = full_text[:4000] + "\n...[Truncated]"
                full_embed = discord.Embed(title="Full Queue", description=full_text, color=discord.Color.blue())
                await inter.response.send_message(embed=full_embed, ephemeral=True, view=FullListView(queue))
            btn_full.callback = full_list_callback
            view.add_item(btn_full)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

    async def cb_mute(self, interaction):
        if self.player.volume > 0:
            self.player.last_vol = self.player.volume
            await self.player.set_volume(0)
        else:
            vol = getattr(self.player, 'last_vol', 50)
            await self.player.set_volume(vol)
        await self.refresh(interaction)

