# cogs/uwulock.py

import discord
from discord.ext import commands
import re
import json
import os
import random
from datetime import datetime


class UwuLock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locked = {}
        self.webhooks = {}
        self.path = "data/uwulock.json"
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    self.locked = {int(k): v for k, v in json.load(f).items()}
        except Exception:
            self.locked = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        try:
            with open(self.path, "w") as f:
                json.dump({str(k): v for k, v in self.locked.items()}, f, indent=2)
        except Exception:
            pass

    async def _get_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        if channel.id in self.webhooks:
            try:
                await self.webhooks[channel.id].fetch()
                return self.webhooks[channel.id]
            except discord.NotFound:
                del self.webhooks[channel.id]

        for wh in await channel.webhooks():
            if wh.user and wh.user.id == self.bot.user.id:
                self.webhooks[channel.id] = wh
                return wh

        wh = await channel.create_webhook(name="UwuLock")
        self.webhooks[channel.id] = wh
        return wh

    async def _cleanup_webhooks(self):
        for wh in list(self.webhooks.values()):
            try:
                await wh.delete()
            except Exception:
                pass
        self.webhooks.clear()

    @staticmethod
    def uwuify(text: str) -> str:
        if not text:
            return ""

        words = text.lower().split()
        safe = []
        for w in words:
            if w.startswith(("http://", "https://", "discord.gg/", "dtlnk.gg/")):
                safe.append(w)
                continue
            if re.match(r"<@!?&?\d+>", w):
                safe.append(w)
                continue
            if len(w) > 2 and w[0].isalpha() and random.random() < 0.25:
                w = f"{w[0]}-{w}"
            safe.append(w)
        t = " ".join(safe)

        t = re.sub(r"[rl]", "w", t)
        t = re.sub(r"ov", "uv", t)
        t = re.sub(r"(?<![a-z])n([bcdfghjklmnpqrstvwxyz])", r"ny\1", t)
        t = t.replace("!", " uwu!")
        t = t.replace("?", " uwu?")
        t = re.sub(r"\.$", "", t).strip()

        if t and not any(t.endswith(x) for x in ("uwu!", "uwu?", "~", "owo", "uwu")):
            if random.random() < 0.35:
                t += random.choice([
                    " (◕‿◕✿)", " (ᵘᵕᵘᵕ)", " OwO", " UwU",
                    " >w<", " (⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)", " ~~",
                ])
        return t

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot or message.webhook_id:
            return
        if message.author.id not in self.locked:
            return

        if message.author.guild_permissions.manage_channels:
            return

        channel = message.channel
        bot_me = channel.guild.me

        if not (bot_me.guild_permissions.manage_webhooks and bot_me.guild_permissions.manage_messages):
            return

        content = message.content
        if not content or not content.strip():
            return

        uwu_text = self.uwuify(content)
        if uwu_text == content.lower().strip():
            return

        try:
            await message.delete()
        except Exception:
            return

        try:
            wh = await self._get_webhook(channel)
            await wh.send(
                content=uwu_text,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception:
            pass

    @commands.command(name="uwulock", aliases=["ulock"])
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, manage_webhooks=True)
    async def uwulock_cmd(self, ctx, member: discord.Member, *, reason: str = "Tidak ada alasan"):
        if member.bot:
            return await ctx.send(embed=discord.Embed(description="❌ Ga bisa uwulock bot.", color=0xFF6B6B))
        if member.guild_permissions.manage_channels:
            return await ctx.send(embed=discord.Embed(description=f"❌ {member.mention} punya **Manage Channels**, ga bisa di-lock.", color=0xFF6B6B))
        if member.id in self.locked:
            info = self.locked[member.id]
            locker = self.bot.get_user(info["by"])
            return await ctx.send(embed=discord.Embed(description=f"❌ {member.mention} sudah di-uwulock oleh {locker.mention if locker else 'Unknown'}!", color=0xFF6B6B))

        self.locked[member.id] = {"by": ctx.author.id, "at": datetime.now().isoformat(), "reason": reason}
        self._save()

        embed = discord.Embed(
            title="🔒✨ Uwulock Aktif!",
            description=f"{member.mention} sekarang di-**UWU LOCK**!\nSetiap pesannya di server ini akan dihapus lalu dikirim ulang sebagai uwu dengan nama & avatar dia sendiri.\n\n**Alasan:** {reason}",
            color=0xFFB3D9, timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Locked by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="uwuunlock", aliases=["uunlock"])
    @commands.has_permissions(manage_channels=True)
    async def uwuunlock_cmd(self, ctx, member: discord.Member):
        if member.id not in self.locked:
            return await ctx.send(embed=discord.Embed(description=f"❌ {member.mention} tidak sedang di-uwulock.", color=0xFF6B6B))

        info = self.locked.pop(member.id)
        self._save()

        locker = self.bot.get_user(info["by"])
        embed = discord.Embed(
            title="🔓 Uwulock Dibuka",
            description=f"{member.mention} sudah bebas. Pesannya kembali normal.",
            color=0x90EE90, timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Di-lock oleh", value=locker.mention if locker else "Unknown")
        embed.add_field(name="Alasan", value=info.get("reason", "-"))
        embed.set_footer(text=f"Unlocked by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="uwulocklist", aliases=["ulocks"])
    @commands.has_permissions(manage_channels=True)
    async def uwulocklist_cmd(self, ctx):
        if not self.locked:
            return await ctx.send(embed=discord.Embed(description="✅ Tidak ada member yang sedang di-uwulock.", color=0x90EE90))

        lines = []
        for uid, info in self.locked.items():
            user = ctx.guild.get_member(uid)
            name = user.mention if user else f"`{uid}` (tidak di server)"
            locker = self.bot.get_user(info["by"])
            lines.append(f"• {name} — oleh **{locker.display_name if locker else 'Unknown'}**")

        embed = discord.Embed(title="🔒 Member Uwulocked", description="\n".join(lines), color=0xFFB3D9, timestamp=datetime.now())
        embed.set_footer(text=f"Total: {len(self.locked)} orang")
        await ctx.send(embed=embed)

    @commands.command(name="uwuify", aliases=["uwu"])
    async def uwuify_cmd(self, ctx, *, text: str = None):
        if not text:
            ref = ctx.message.reference
            if ref and ref.resolved:
                text = ref.resolved.content
            if not text or not text.strip():
                return await ctx.send(embed=discord.Embed(description="❌ Kasih teks atau reply pesan.", color=0xFF6B6B))

        embed = discord.Embed(description=self.uwuify(text), color=0xFFB3D9)
        embed.set_author(name=f"{ctx.author.display_name} uwuified", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    def cog_unload(self):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._cleanup_webhooks())
        except RuntimeError:
            pass


async def setup(bot):
    await bot.add_cog(UwuLock(bot))
