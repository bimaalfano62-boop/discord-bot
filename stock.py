import discord
from discord.ext import commands, tasks
import asyncio
import json
import time

STOCK_FILE = "stock.json"

def load_data():
    try:
        with open(STOCK_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "fruits": [],
            "reset_time": 0,
            "channel_id": None
        }

def save_data(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_timer.start()

    def cog_unload(self):
        self.check_timer.cancel()

    # =========================
    # ADD STOCK + TIMER (1 FLOW)
    # =========================
    @commands.command()
    async def addstock(self, ctx):
        data = load_data()

        await ctx.send("🍇 Send fruit names separated by comma\nExample: `Dragon, Leopard, Dough`")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            fruits = [f.strip() for f in msg.content.split(",")]

            data["fruits"] = fruits
            data["channel_id"] = ctx.channel.id

            await ctx.send("⏳ Now send timer in minutes (example: `30`)")

            msg2 = await self.bot.wait_for("message", timeout=60, check=check)
            minutes = int(msg2.content)

            reset_time = int(time.time()) + (minutes * 60)
            data["reset_time"] = reset_time

            save_data(data)

            await ctx.send(f"✅ Stock set!\nFruits: {', '.join(fruits)}\nTimer: {minutes} minutes")

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

        minutes = remaining // 60
        seconds = remaining % 60

        await ctx.send(
            f"🍇 **Current Stock:**\n{', '.join(data['fruits'])}\n\n⏳ Reset in: {minutes}m {seconds}s"
        )

    # =========================
    # HOW TO USE
    # =========================
    @commands.command()
    async def howstock(self, ctx):
        await ctx.send(
            "**📘 HOW TO USE STOCK SYSTEM**\n\n"
            "`!addstock`\n"
            "→ Input fruits (example: Dragon, Dough, Leopard)\n"
            "→ Input timer (minutes)\n\n"
            "`!stock`\n"
            "→ Show current fruits + countdown timer\n\n"
            "⚙️ System:\n"
            "- Timer countdown\n"
            "- Auto reset after time ends\n"
            "- ⚠️ Notification before stock reset"
        )

    # =========================
    # TIMER LOOP + NOTIF
    # =========================
    @tasks.loop(seconds=10)
    async def check_timer(self):
        data = load_data()

        if data["reset_time"] == 0 or not data["channel_id"]:
            return

        now = int(time.time())
        remaining = data["reset_time"] - now

        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return

        # ⚠️ NOTIFICATION 60 SECONDS BEFORE RESET
        if 50 <= remaining <= 60:
            await channel.send("⚠️ Stock will reset in **1 minute!**")

        # 🔥 RESET STOCK
        if remaining <= 0:
            data["fruits"] = []
            data["reset_time"] = 0
            save_data(data)

            await channel.send("🔄 Stock has been reset!")

    @check_timer.before_loop
    async def before_timer(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Stock(bot))
