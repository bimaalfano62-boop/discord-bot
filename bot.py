import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# LOAD ENV
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# ✅ FIX INTENTS
intents = discord.Intents.default()
intents.message_content = True  # IMPORTANT

bot = commands.Bot(command_prefix="!", intents=intents)


# LOAD COGS
async def main():
    async with bot:
        await bot.load_extension("ai")     # AI + Wiki
        await bot.load_extension("stock")  # 🔥 Stock system
        await bot.start(TOKEN)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(e)


asyncio.run(main())
