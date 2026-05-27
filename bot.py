import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv  # ✅ TAMBAHIN INI

# LOAD ENV
load_dotenv()  # ✅ WAJIB

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# LOAD COG
async def main():
    async with bot:
        await bot.load_extension("ai")  # file ai.py
        await bot.start(TOKEN)

# 🔥 SYNC COMMAND (BIAR /HELP MUNCUL)
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(e)

asyncio.run(main())
