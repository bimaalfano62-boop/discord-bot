import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# LOAD ENV
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# INTENTS
intents = discord.Intents.default()
intents.message_content = True  # 🔥 WAJIB buat command !

bot = commands.Bot(command_prefix="!", intents=intents)

# MAIN
async def main():
    async with bot:
        await bot.load_extension("ai")      # ai.py lu
        await bot.load_extension("stock")   # ✅ stock.py
        await bot.start(TOKEN)

# READY
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)

asyncio.run(main())
