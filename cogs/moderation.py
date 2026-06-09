import discord
import asyncio
import random
from discord.ext import commands
from datetime import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    async def purge_cmd(self, ctx, amount: int = 10):
        if amount > 100: return await ctx.send("❌ Maximum 100 messages!")
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=self.embed_builder("🗑️ Purge", f"Deleted `{len(deleted)-1}` messages!"))
        await asyncio.sleep(3); await msg.delete()

    @commands.command(name="embed")
    @commands.has_permissions(manage_messages=True)
    async def embed_cmd(self, ctx, *, text):
        await ctx.send(embed=self.embed_builder("💬 Embed Message", text, color=random.randint(0, 0xffffff)))
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(Moderation(bot))
