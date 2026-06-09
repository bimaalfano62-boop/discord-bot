import discord
from discord.ext import commands
from datetime import datetime

class SnipeAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="snipe")
    async def snipe_cmd(self, ctx):
        data = self.bot.sniped_messages.get(ctx.channel.id)
        if not data: return await ctx.send("❌ No messages to snipe!")
        em = discord.Embed(title="🔍 Sniped!", description=data["content"] or "*No text*", color=0xff9900, timestamp=data["time"])
        em.set_footer(text=f"{data['author']} • ID: {data['author'].id}")
        if data["attachments"]: em.set_image(url=data["attachments"][0].url)
        await ctx.send(embed=em)

    @commands.command(name="editsnipe", aliases=["esnipe"])
    async def editsnipe_cmd(self, ctx):
        data = self.bot.edited_messages.get(ctx.channel.id)
        if not data: return await ctx.send("❌ No edited messages!")
        em = discord.Embed(title="✏️ Edit Sniped!", color=0xff9900, timestamp=data["time"])
        em.add_field(name="Before", value=data["before"] or "*Empty*", inline=False)
        em.add_field(name="After", value=data["after"] or "*Empty*", inline=False)
        em.set_footer(text=f"{data['author']} • ID: {data['author'].id}")
        await ctx.send(embed=em)

    @commands.command(name="afk")
    @commands.has_permissions(administrator=True)
    async def afk_cmd(self, ctx, *, action="on"):
        if action.lower() in ["off", "disable"]:
            self.bot.afk["enabled"] = False; self.bot.config["afk"]["enabled"] = False
            self.bot.save_config(self.bot.config); em = self.embed_builder("💤 AFK", "AFK **disabled**")
        elif action.lower() in ["on", "enable"]:
            self.bot.afk["enabled"] = True; self.bot.afk["message"] = "I'm currently AFK"
            self.bot.config["afk"]["enabled"] = True; self.bot.config["afk"]["message"] = "I'm currently AFK"
            self.bot.save_config(self.bot.config); em = self.embed_builder("💤 AFK", "AFK **enabled**")
        else:
            self.bot.afk["enabled"] = True; self.bot.afk["message"] = action
            self.bot.config["afk"]["enabled"] = True; self.bot.config["afk"]["message"] = action
            self.bot.save_config(self.bot.config); em = self.embed_builder("💤 AFK", f"AFK **enabled**\nMessage: `{action}`")
        await ctx.send(embed=em)

    @commands.command(name="autoreply")
    @commands.has_permissions(administrator=True)
    async def autoreply_cmd(self, ctx, action="on"):
        if action.lower() in ["off", "disable"]:
            self.bot.auto_reply["enabled"] = False; self.bot.config["auto_reply"]["enabled"] = False
            self.bot.save_config(self.bot.config); em = self.embed_builder("💬 Auto Reply", "Auto Reply **disabled**")
        else:
            self.bot.auto_reply["enabled"] = True; self.bot.config["auto_reply"]["enabled"] = True
            self.bot.save_config(self.bot.config)
            triggers = "\n".join([f"`{k}` → `{v}`" for k, v in self.bot.auto_reply.get("triggers", {}).items()]) or "Empty"
            em = self.embed_builder("💬 Auto Reply", f"Auto Reply **enabled**\n\n**Triggers:**\n{triggers}")
        await ctx.send(embed=em)

    @commands.command(name="addtrigger")
    @commands.has_permissions(administrator=True)
    async def addtrigger_cmd(self, ctx, *, text):
        parts = text.split("|")
        if len(parts) < 2: return await ctx.send("❌ Format: `addtrigger trigger|reply`")
        trigger, reply = parts[0].strip(), "|".join(parts[1:]).strip()
        self.bot.auto_reply.setdefault("triggers", {})[trigger] = reply
        self.bot.config["auto_reply"]["triggers"][trigger] = reply
        self.bot.save_config(self.bot.config)
        await ctx.send(embed=self.embed_builder("✅ Trigger Added", f"`{trigger}` → `{reply}`"))

    @commands.command(name="antidelete")
    @commands.has_permissions(administrator=True)
    async def antidelete_cmd(self, ctx, action="on", channel: discord.TextChannel = None):
        if action.lower() in ["off", "disable"]:
            self.bot.anti_delete["enabled"] = False; self.bot.config["anti_delete"]["enabled"] = False
            self.bot.save_config(self.bot.config); em = self.embed_builder("🛡️ Anti Delete", "Anti Delete **disabled**")
        else:
            ch = channel or ctx.channel; self.bot.anti_delete["enabled"] = True; self.bot.anti_delete["channel_id"] = str(ch.id)
            self.bot.config["anti_delete"]["enabled"] = True; self.bot.config["anti_delete"]["channel_id"] = str(ch.id)
            self.bot.save_config(self.bot.config); em = self.embed_builder("🛡️ Anti Delete", f"Anti Delete **enabled**\nLog Channel: {ch.mention}")
        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(SnipeAuto(bot))
