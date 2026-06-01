import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from stock import StockView

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        bot.add_view(StockView())
        print("✅ StockView registered")
    except Exception as e:
        print(f"StockView error: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Slash sync error: {e}")

async def main():
    async with bot:
        await bot.load_extension("ai")
        await bot.load_extension("stock")
        await bot.load_extension("Troll")
        await bot.load_extension("blox_stock")
        await bot.load_extension("katla")
        await bot.start(TOKEN)

asyncio.run(main())
