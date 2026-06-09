import discord
import time
from discord.ext import commands
from datetime import datetime

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="ping")
    async def ping_cmd(self, ctx):
        start = time.perf_counter(); msg = await ctx.send("🏓 Pinging...")
        end = time.perf_counter(); latency = round((end - start) * 1000)
        api_lat = round(self.bot.latency * 1000)
        em = self.embed_builder("🏓 Pong!", f"**Latency:** `{latency}ms`\n**API:** `{api_lat}ms`")
        await msg.edit(content=None, embed=em)

    @commands.command(name="uptime")
    async def uptime_cmd(self, ctx):
        if not self.bot.start_time: return await ctx.send("N/A")
        delta = datetime.now() - self.bot.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        await ctx.send(embed=self.embed_builder("⏰ Uptime", f"`{hours}h {minutes}m {seconds}s`"))

    @commands.command(name="about", aliases=["botinfo"])
    async def about_cmd(self, ctx):
        em = discord.Embed(title="🤖 AI Groq Bot", description="An all-in-one AI-powered Bot using ultra-fast Groq API.", color=0x5865F2, timestamp=datetime.now())
        em.add_field(name="🧠 AI Engine", value="Groq", inline=True)
        em.add_field(name="🏠 Servers", value=f"{len(self.bot.guilds)}", inline=True)
        await ctx.send(embed=em)

    @commands.command(name="userinfo", aliases=["ui"])
    async def userinfo_cmd(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        em = discord.Embed(title=f"👤 {user}", color=user.color, timestamp=datetime.now())
        em.set_thumbnail(url=user.avatar.url if user.avatar else "")
        em.add_field(name="ID", value=user.id, inline=True)
        em.add_field(name="Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
        em.add_field(name="Joined", value=f"<t:{int(user.joined_at.timestamp())}:R>", inline=True)
        await ctx.send(embed=em)

    @commands.command(name="avatar", aliases=["av"])
    async def avatar_cmd(self, ctx, user: discord.User = None):
        user = user or ctx.author
        if not user.avatar: return await ctx.send("❌ No avatar!")
        await ctx.send(embed=self.embed_builder("🖼️ Avatar", f"[Download]({user.avatar.url})", color=0x00ff00).set_image(url=user.avatar.url))

async def setup(bot):
    await bot.add_cog(Utility(bot))
