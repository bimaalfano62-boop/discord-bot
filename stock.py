import discord
from discord.ext import commands
import asyncio
import random

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stock_data = {}
        self.timer_task = None

    # =========================
    # 🧠 TIME PARSER (HH:MM:SS)
    # =========================
    def parse_time(self, time_str: str) -> int:
        parts = list(map(int, time_str.split(":")))

        if len(parts) == 1:
            return parts[0]  # seconds
        elif len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError("Invalid time format")

    # =========================
    # 🎲 RANDOM EMOJI (BASED ON NAME)
    # =========================
    def get_random_emoji(self, text: str) -> str:
        emojis = ["🔥","⚡","💀","👀","✨","🧠","💥","🚀","😈","📦","🎯","🌀"]
        random.seed(text.lower())  # makes it consistent per name
        return random.choice(emojis)

    # =========================
    # ➕ CREATE STOCK
    # =========================
    @commands.hybrid_command(name="addstock", description="Create a new stock category")
    async def addstock(self, ctx, name: str):
        if name not in self.stock_data:
            self.stock_data[name] = []
            await ctx.send(f"✅ Stock `{name}` created!")
        else:
            await ctx.send("⚠️ Stock already exists")

    # =========================
    # 📥 INPUT STOCK ITEMS
    # =========================
    @commands.hybrid_command(name="stockin", description="Add items to stock")
    async def stockin(self, ctx, name: str):
        if name not in self.stock_data:
            await ctx.send("❌ Stock not found")
            return

        await ctx.send("📥 Send stock items (type `done` to finish)")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
            msg = await self.bot.wait_for("message", check=check)

            if msg.content.lower() == "done":
                break

            self.stock_data[name].append(msg.content)

        await ctx.send(f"✅ Stock `{name}` updated!")

    # =========================
    # 📦 VIEW STOCK COUNT
    # =========================
    @commands.hybrid_command(name="stock", description="Check stock amount")
    async def stock(self, ctx, name: str):
        if name not in self.stock_data:
            await ctx.send("❌ Stock not found")
            return

        emoji = self.get_random_emoji(name)
        amount = len(self.stock_data[name])

        await ctx.send(f"{emoji} `{name}` available: **{amount}**")

    # =========================
    # 📤 CLAIM STOCK
    # =========================
    @commands.hybrid_command(name="claim", description="Claim one stock item")
    async def claim(self, ctx, name: str):
        if name not in self.stock_data or not self.stock_data[name]:
            await ctx.send("❌ Stock is empty")
            return

        item = self.stock_data[name].pop(0)

        try:
            await ctx.author.send(f"📦 Your `{name}` item:\n{item}")
            await ctx.send("✅ Check your DM!")
        except:
            await ctx.send("❌ Couldn't send DM (are your DMs closed?)")

    # =========================
    # ⏱️ AUTO CLEAR TIMER
    # =========================
    async def stock_timer(self, seconds: int):
        await asyncio.sleep(seconds)
        self.stock_data.clear()

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    await channel.send("🧹 Stock has been auto-cleared!")
                    return
                except:
                    continue

    @commands.hybrid_command(name="settimer", description="Set auto-clear timer (HH:MM:SS)")
    async def settimer(self, ctx, time: str):
        try:
            seconds = self.parse_time(time)
        except:
            await ctx.send("❌ Invalid format. Use HH:MM:SS / MM:SS / SS")
            return

        if self.timer_task:
            self.timer_task.cancel()

        self.timer_task = asyncio.create_task(self.stock_timer(seconds))

        await ctx.send(f"⏱️ Timer set to `{time}` ({seconds} seconds)")

    # =========================
    # 🧹 MANUAL CLEAR
    # =========================
    @commands.hybrid_command(name="clearstock", description="Clear all stock")
    async def clearstock(self, ctx):
        self.stock_data.clear()
        await ctx.send("🧹 All stock cleared!")


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Stock(bot))
