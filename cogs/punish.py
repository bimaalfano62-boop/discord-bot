# cogs/punish.py

import discord
from discord.ext import commands
import re
import json
import os
import random
from datetime import datetime


class Punish(commands.Cog):
    """Lock a user into a specific speaking mode (uwu, zesty, or brainrot)."""

    MODES = ["uwu", "zesty", "brainrot"]

    def __init__(self, bot):
        self.bot = bot
        # {user_id: {"mode": str, "by": int, "at": str, "reason": str}}
        self.locked = {}
        self.webhooks = {}
        self.path = "data/punish_data.json"
        self._load()

    # ── Persistence ──────────────────────────────────

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

    # ── Webhook Helper ───────────────────────────────

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

        wh = await channel.create_webhook(name="PunishWebhook")
        self.webhooks[channel.id] = wh
        return wh

    async def _cleanup_webhooks(self):
        for wh in list(self.webhooks.values()):
            try:
                await wh.delete()
            except Exception:
                pass
        self.webhooks.clear()

    # ── Text Conversion Engines ──────────────────────

    @staticmethod
    def _to_uwu(text: str) -> str:
        if not text: return ""
        words = text.lower().split()
        safe = []
        for w in words:
            if w.startswith(("http://", "https://")) or re.match(r"<@!?&?\d+>", w):
                safe.append(w)
                continue
            if len(w) > 2 and w[0].isalpha() and random.random() < 0.25:
                w = f"{w[0]}-{w}"
            safe.append(w)
        t = " ".join(safe)
        t = re.sub(r"[rl]", "w", t)
        t = re.sub(r"ov", "uv", t)
        t = re.sub(r"(?<![a-z])n([bcdfghjklmnpqrstvwxyz])", r"ny\1", t)
        t = t.replace("!", " uwu!").replace("?", " uwu?")
        t = re.sub(r"\.$", "", t).strip()
        if t and not any(t.endswith(x) for x in ("uwu!", "uwu?", "~", "owo", "uwu")):
            if random.random() < 0.35:
                t += random.choice([" (◕‿◕✿)", " (ᵘᵕᵘᵕ)", " OwO", " UwU", " >w<", " ~~"])
        return t

    @staticmethod
    def _to_zesty(text: str) -> str:
        if not text: return ""
        t = text.lower()
        
        zesty_words = {
            "yes": "yasss", "no": "chile no", "okay": "okurrr", "ok": "okurrr",
            "girl": "gyat", "bro": "pookie", "brother": "pookie",
            "crazy": "delulu", "delusional": "delulu", "good": "slay", "great": "slayed",
            "bad": "a mess", "ugly": "raggedy", "pretty": "serving cunt",
            "like": "literally", "love": "obsessed with", "hate": "sick of",
            "mad": "pressed", "angry": "pressed", "scared": "shaking and crying",
            "look": "serve", "looking": "serving", "winning": "eating it up",
            "losing": "bombing", "stop": "put a sock in it", "shut up": "put a sock in it",
            "really": "literally", "very": "sooo", "much": "tons of",
            "wrong": "bogus", "right": "mother",
        }
        
        for k, v in zesty_words.items():
            t = re.sub(rf"\b{k}\b", v, t)

        t = re.sub(r"!+", " 💅✨!", t)
        t = re.sub(r"\?+", " 🙄?", t)
        
        if t and random.random() < 0.3:
            t += random.choice([
                " 💅✨", " and it's giving!", " period.", " slay!", 
                " no cap.", " literally shaking."
            ])
        return t

    @staticmethod
    def _to_brainrot(text: str) -> str:
        if not text: return ""
        t = text.lower()
        
        brainrot_dict = {
            "good": "skibidi", "bad": "negative aura", "crazy": "skibidi toilet",
            "what": "what the sigma", "why": "why the sigma", "how": "how the sigma",
            "yes": "yessir skibidi", "no": "naw bro cap",
            "bro": "skibidi bro", "girl": "skibidi rizzler", "boy": "skibidi rizzler",
            "cool": "sigma", "idiot": "npc", "stupid": "npc",
            "money": "mogging", "win": "absolute w", "lose": "massive L",
            "like": "fr fr", "really": "deadass", "very": "mad fr fr",
            "look at": "mire at", "go": "bussin", "going": "bussin",
            "eat": "devour", "food": "bussin", "nice": "rizz",
            "girlfriend": "gyatt", "boyfriend": "gyatt",
            "scared": "fanum taxed", "rob": "fanum tax", "steal": "fanum tax",
        }
        
        for k, v in brainrot_dict.items():
            t = re.sub(rf"\b{k}\b", v, t)

        # Add random brainrot slang at the end
        if t and random.random() < 0.4:
            t += random.choice([
                " skibidi toilet 🚽", " ohio 💀", " rizz 🗣️",
                " aura +10000 ✨", " no cap 🧢", " fr fr 💀",
                " mewing 😋", " edging 🫠", " goon 🔥"
            ])
            
        return t

    def convert_text(self, text: str, mode: str) -> str:
        if mode == "uwu": return self._to_uwu(text)
        if mode == "zesty": return self._to_zesty(text)
        if mode == "brainrot": return self._to_brainrot(text)
        return text

    # ── Listener ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot or message.webhook_id:
            return
        if message.author.id not in self.locked:
            return

        channel = message.channel
        bot_me = channel.guild.me
        if not (bot_me.guild_permissions.manage_webhooks and bot_me.guild_permissions.manage_messages):
            return

        content = message.content
        if not content or not content.strip():
            return

        mode = self.locked[message.author.id]["mode"]
        converted = self.convert_text(content, mode)
        
        if converted.lower().strip() == content.lower().strip():
            return

        try:
            await message.delete()
        except Exception:
            return

        try:
            wh = await self._get_webhook(channel)
            await wh.send(
                content=converted,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception:
            pass

    # ── Command: !punish ─────────────────────────────

    @commands.command(
        name="punish",
        brief="Lock a user into a specific typing mode (uwu, zesty, brainrot)",
        usage="@member <mode> [reason]",
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, manage_webhooks=True)
    async def punish_cmd(self, ctx, member: discord.Member, mode: str, *, reason: str = "No reason provided"):
        mode = mode.lower()
        if mode not in self.MODES:
            return await ctx.send(
                embed=discord.Embed(
                    description=f"❌ Invalid mode! Choose from: **{', '.join(self.MODES)}**",
                    color=0xFF6B6B
                )
            )

        if member.bot:
            return await ctx.send(embed=discord.Embed(description="❌ Cannot punish a bot.", color=0xFF6B6B))

        if member.id in self.locked:
            info = self.locked[member.id]
            locker = self.bot.get_user(info["by"])
            return await ctx.send(
                embed=discord.Embed(
                    description=f"❌ {member.mention} is already punished with **{info['mode']}** mode by {locker.mention if locker else 'Unknown'}!",
                    color=0xFF6B6B
                )
            )

        self.locked[member.id] = {
            "mode": mode,
            "by": ctx.author.id,
            "at": datetime.now().isoformat(),
            "reason": reason,
        }
        self._save()

        mode_desc = {
            "uwu": "Every message will be deleted and sent back in **UwU** format.",
            "zesty": "Every message will be deleted and sent back in **Zesty/Sassy** format.",
            "brainrot": "Every message will be deleted and sent back in **Brainrot/Sigma** format."
        }

        embed = discord.Embed(
            title="🔨 Punished!",
            description=(
                f"{member.mention} has been locked to **{mode.upper()}** mode!\n"
                f"{mode_desc.get(mode, '')}\n\n"
                f"**Reason:** {reason}"
            ),
            color=0xFFB3D9,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Punished by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ── Command: !unpunish ───────────────────────────

    @commands.command(
        name="unpunish",
        brief="Remove the punishment from a user",
        usage="@member",
    )
    @commands.has_permissions(manage_channels=True)
    async def unpunish_cmd(self, ctx, member: discord.Member):
        if member.id not in self.locked:
            return await ctx.send(
                embed=discord.Embed(
                    description=f"❌ {member.mention} is not currently punished.",
                    color=0xFF6B6B
                )
            )

        info = self.locked.pop(member.id)
        self._save()

        locker = self.bot.get_user(info["by"])
        embed = discord.Embed(
            title="🔓 Unpunished",
            description=f"{member.mention} is free. Their messages are back to normal.",
            color=0x90EE90,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Previous Mode", value=info["mode"].upper())
        embed.add_field(name="Punished by", value=locker.mention if locker else "Unknown")
        embed.add_field(name="Reason", value=info.get("reason", "-"))
        embed.set_footer(text=f"Unpunished by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ── Command: !punishlist ─────────────────────────

    @commands.command(
        name="punishlist",
        brief="See all punished users in the server",
    )
    @commands.has_permissions(manage_channels=True)
    async def punishlist_cmd(self, ctx):
        if not self.locked:
            return await ctx.send(
                embed=discord.Embed(
                    description="✅ No one is currently punished.",
                    color=0x90EE90
                )
            )

        lines = []
        for uid, info in self.locked.items():
            user = ctx.guild.get_member(uid)
            name = user.mention if user else f"`{uid}` (not in server)"
            locker = self.bot.get_user(info["by"])
            lines.append(f"• {name} — **[{info['mode'].upper()}]** by {locker.display_name if locker else 'Unknown'}")

        embed = discord.Embed(
            title="🔨 Punished Users",
            description="\n".join(lines),
            color=0xFFB3D9,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"Total: {len(self.locked)} users")
        await ctx.send(embed=embed)

    # ── Cleanup ──────────────────────────────────────

    def cog_unload(self):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._cleanup_webhooks())
        except RuntimeError:
            pass


async def setup(bot):
    await bot.add_cog(Punish(bot))
