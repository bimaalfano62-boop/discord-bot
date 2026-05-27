import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# LOAD ENV
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# ✅ INTENTS
intents = discord.Intents.default()
intents.message_content = True  # IMPORTANT

bot = commands.Bot(command_prefix="!", intents=intents)


# =========================
# LOAD COGS
# =========================
async def main():
    async with bot:
        await bot.load_extension("ai")     # AI + Wiki
        await bot.load_extension("stock")  # Stock system
        await bot.start(TOKEN)


# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # 🔥 IMPORTANT: Sync Stock Buttons (FIX INTERACTION FAILED)
    try:
        from stock import StockView   # if using cogs -> from cogs.stock import StockView
        bot.add_view(StockView())
    except Exception as e:
        print(f"StockView load error: {e}")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(e)


# =========================
# RUN BOT
# =========================
asyncio.run(main())
