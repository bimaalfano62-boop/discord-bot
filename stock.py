import discord
from discord.ext import commands, tasks
import asyncio
import json
import time
import re
import random

STOCK_FILE = "stock.json"

# =========================
# EMOJI LIST (RANDOM)
# =========================
FRUIT_EMOJIS = ["🍎","🍊","🍇","🍉","🍍","🥭","🍒","🍑","🍓","🥝","🍌","🥥"]

# =========================
# LOAD & SAVE
# =========================
def load_data():
    try:
        with open(STOCK_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "fruits": [],
            "reset_time": 0,
            "channel_id": None,
            "notified": False
        }

def save_data(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# PARSE TIMER
# =========================
def parse_time(time_str):
    time_str = time_str.lower()

    hours = minutes = seconds = 0

    h = re.findall(r'(\d+)\s*(h|jam)', time_str)
    m = re.findall(r'(\d+)\s*(m|menit)', time_str)
    s = re.findall(r'(\d+)\s*(s|detik)', time_str)

    if h:
        hours = int(h[0][0])
    if m:
        minutes = int(m[0][0])
    if s:
        seconds = int(s[0][0])

    if not (h or m or s):
        minutes = int(time_str)

    return hours * 3600 + minutes * 60 + seconds

# =========================
# FORMAT FRUITS WITH EMOJI
# =========================
def format_fruits(fruits):
    result = []
    for fruit in fruits:
        emoji = random.choice(FRUIT_EMOJIS)
        result.append(f"{emoji} {fruit}")
    return "\n".join(result)

# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_timer.start()

    def cog_unload(self):
        self.check_timer.cancel()

    # =========================
    # ADD STOCK
    # =========================
    @commands.command()
    async def addstock(self, ctx):
        data = load_data()

        await ctx.send("🍇 Send fruit names (comma separated)\nExample: Dragon, Leopard, Dough")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            fruits = [f.strip() for f in msg.content.split(",")]

            data["fruits"] = fruits
            data["channel_id"] = ctx.channel.id

            await ctx.send("⏳ Send timer (example: 30m / 1h 20m / 45s)")

            msg2 = await self.bot.wait_for("message", timeout=60, check=check)

            total_seconds = parse_time(msg2.content)
            reset_time = int(time.time()) + total_seconds

            data["reset_time"] = reset_time
            data["notified"] = False

            save_data(data)

            await ctx.send(
                f"✅ Stock set!\n\n"
                f"{format_fruits(fruits)}\n\n"
                f"⏳ Timer: {msg2.content}"
            )

        except asyncio.TimeoutError:
            await ctx.send("❌ You took too long.")

    # =========================
    # SHOW STOCK
    # =========================
    @commands.command()
    async def stock(self, ctx):
        data = load_data()

        if not data["fruits"]:
            await ctx.send("❌ No stock available.")
            return

        remaining = data["reset_time"] - int(time.time())

        if remaining <= 0:
            await ctx.send("⚠️ Stock expired.")
            return

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60

        await ctx.send(
            f"🍇 **Current Stock:**\n\n"
            f"{format_fruits(data['fruits'])}\n\n"
            f"⏳ Reset in: {hours}h {minutes}m {seconds}s"
        )

    # =========================
    # HOW TO USE
    # =========================
    @commands.command()
    async def howstock(self, ctx):
        await ctx.send(
            "**📘 HOW TO USE STOCK SYSTEM**\n\n"
            "`!addstock`\n"
            "→ Input fruits (Dragon, Leopard, Dough)\n"
            "→ Input timer (1h 20m / 30m / 45s)\n\n"
            "`!stock`\n"
            "→ Show stock + countdown\n\n"
            "⚙️ Features:\n"
            "- Random emoji tiap fruit\n"
            "- Countdown timer\n"
            "- Auto reset\n"
            "- Notification sebelum reset"
        )

    # =========================
    # TIMER LOOP
    # =========================
    @tasks.loop(seconds=5)
    async def check_timer(self):
        data = load_data()

        if data["reset_time"] == 0 or not data["channel_id"]:
            return

        now = int(time.time())
        remaining = data["reset_time"] - now

        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return

        # 🔔 NOTIF 1 MENIT
        if remaining <= 60 and remaining > 0 and not data.get("notified"):
            await channel.send("⚠️ Stock will reset in **1 minute!**")
            data["notified"] = True
            save_data(data)

        # 🔄 RESET
        if remaining <= 0:
            data["fruits"] = []
            data["reset_time"] = 0
            data["notified"] = False
            save_data(data)

            await channel.send("🔄 Stock has been reset!")

    @check_timer.before_loop
    async def before_timer(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Stock(bot))
