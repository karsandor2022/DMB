import discord
from discord.ext import commands
import wavelink
from cogs.controls import PlayerControls
from utils import database, helpers

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, search: str):
        if not ctx.voice_client:
            if not ctx.author.voice:
                return await ctx.send("Join a voice channel first!")
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            
            # Load Persistent Settings
            settings = await database.get_settings(ctx.guild.id)
            await player.set_volume(settings['volume'])
            await helpers.apply_eq(player, settings['eq_preset'])
        else:
            player = ctx.voice_client

        tracks = await wavelink.Playable.search(search)
        if not tracks: return await ctx.send("No results.")
        
        track = tracks[0] if isinstance(tracks, list) else tracks

        if isinstance(tracks, wavelink.Playlist):
            for t in tracks: await player.queue.put_wait(t)
            await ctx.send(f"Added playlist: **{tracks.name}**")
        else:
            await player.queue.put_wait(track)
            if player.playing:
                await ctx.send(f"Added **{track.title}** to queue.")

        if not player.playing:
            await player.play(player.queue.get())
            embed = discord.Embed(
                description=f"Now Playing: **{track.title}**\n{helpers.create_progress_bar(player)}",
                color=discord.Color.green()
            )
            if track.artwork: embed.set_thumbnail(url=track.artwork)
            
            settings = await database.get_settings(ctx.guild.id)
            embed.set_footer(text=f"EQ: {settings['eq_preset'].title()} | Vol: {settings['volume']}%")
            
            await ctx.send(embed=embed, view=PlayerControls(player))

    @commands.command()
    async def setlist(self, ctx, size: int):
        if 1 <= size <= 25:
            await database.update_setting(ctx.guild.id, "list_size", size)
            await ctx.send(f"✅ List button will now show **{size}** songs.")
        else: await ctx.send("❌ Choose between 1 and 25.")

    @commands.command()
    async def setstep(self, ctx, step: int):
        if 1 <= step <= 50:
            await database.update_setting(ctx.guild.id, "vol_step", step)
            await ctx.send(f"✅ Volume buttons will now change by **{step}%**.")
        else: await ctx.send("❌ Choose between 1 and 50.")

async def setup(bot):
    await bot.add_cog(Music(bot))