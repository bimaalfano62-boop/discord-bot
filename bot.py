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

async def main():
    async with bot:
        await bot.load_extension("ai")
        await bot.load_extension("stock")
        await bot.load_extension("Troll")  # load sebelum bot.start()
        await bot.start(TOKEN)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # Fix StockView persistent buttons
    try:
        bot.add_view(StockView(bot))
    except Exception as e:
        print(f"StockView error: {e}")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)

asyncio.run(main())
