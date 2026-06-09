import discord
from discord.ext import commands
from datetime import datetime

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="setprefix")
    @commands.has_permissions(administrator=True)
    async def setprefix_cmd(self, ctx, new_prefix):
        self.bot.command_prefix = [new_prefix, ","]
        self.bot.config["prefix"] = new_prefix
        self.bot.save_config(self.bot.config)
        await ctx.send(embed=self.embed_builder("⚙️ Prefix Changed", f"Primary prefix set to: `{new_prefix}`\n(Note: `,` will still work)"))

    @commands.command(name="setstatus")
    @commands.has_permissions(administrator=True)
    async def setstatus_cmd(self, ctx, status_type, *, text):
        status_type = status_type.lower()
        if status_type == "playing": act = discord.Game(name=text)
        elif status_type == "listening": act = discord.Activity(type=discord.ActivityType.listening, name=text)
        elif status_type == "watching": act = discord.Activity(type=discord.ActivityType.watching, name=text)
        elif status_type == "clear": await self.bot.change_presence(activity=None); return await ctx.send("🗑️ Status cleared!")
        else: return await ctx.send("❌ Types: playing/listening/watching/clear")
        await self.bot.change_presence(activity=act)
        self.bot.config["status"] = {"type": status_type, "text": text}
        self.bot.save_config(self.bot.config)
        await ctx.send(embed=self.embed_builder("⚙️ Status Changed", f"**Type:** {status_type}\n**Text:** {text}"))

    @commands.command(name="help")
    async def help_cmd(self, ctx):
        p = ctx.prefix
        em = self.embed_builder("📖 Bot Commands", f"Prefix: `{p}` (Also works with `!` and `,`)")
        categories = {
            "🤖 AI": [f"`{p}ask`", f"`{p}aimodel`", f"`{p}aitoggle`", f"`{p}aiprompt`", f"`{p}aiconfig`"],
            "🛠️ Utility": [f"`{p}ping`", f"`{p}uptime`", f"`{p}userinfo`", f"`{p}avatar`", f"`{p}about`"],
            "💬 Moderation": [f"`{p}purge`", f"`{p}embed`"],
            "🔥 Fun": [f"`{p}roast`", f"`{p}8ball`", f"`{p}roll`", f"`{p}coinflip`", f"`{p}rps`", f"`{p}gayrate`"],
            "🔍 Snipe & Auto": [f"`{p}snipe`", f"`{p}editsnipe`", f"`{p}afk`", f"`{p}autoreply`", f"`{p}addtrigger`", f"`{p}antidelete`"],
            "📞 Yggdrasil": [f"`{p}phone`"],
            "⚙️ Settings": [f"`{p}setprefix`", f"`{p}setstatus`"],
        }
        for cat, cmds in categories.items():
            em.add_field(name=cat, value="\n".join(cmds), inline=False)
        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(Settings(bot))
