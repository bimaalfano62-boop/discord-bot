import discord
from discord.ext import commands
import aiohttp
import json

# =========================
# BLOX FRUITS STOCK COG
# =========================
class BloxStock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔥 TRANSLATE DARI JAVASCRIPT FETCH KE PYTHON AIOHTTP
    async def fetch_blox_stock(self):
        url = 'https://blox-fruits-api.onrender.com/api/bloxfruits/stock'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle kalau API nya nyimpen JSON string di dalem JSON (kayak di JS lu)
                        if isinstance(data, str):
                            data = json.loads(data)
                            
                        return data
                    else:
                        print(f"Blox Fruits API Error: Status {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching Blox Fruits stock: {e}")
            return None

    # =========================
    # /bloxstock COMMAND
    # =========================
    @discord.app_commands.command(name="bloxstock", description="Check current Blox Fruits Live Stock")
    async def bloxstock(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        
        stock_data = await self.fetch_blox_stock()

        if not stock_data:
            return await interaction.followup.send("❌ Failed to fetch Blox Fruits stock. The API might be down or sleeping (Render free tier sleeps after inactivity).", ephemeral=True)

        # 🔥 FORMAT TAMPILAN DI DISCORD
        embed = discord.Embed(
            title="🍎 Blox Fruits Live Stock",
            color=0x3498DB
        )

        # Karena gue gak tau bentuk persis JSON dari API itu apa, 
        # kita buat dynamic formatter.
        # Kalau datanya berupa list/array:
        if isinstance(stock_data, list):
            if len(stock_data) == 0:
                embed.description = "```\nNo fruits in stock right now.\n```"
            else:
                text = ""
                for item in stock_data:
                    # Kalau itemnya cuma string (e.g. ["Dragon", "Dough"])
                    if isinstance(item, str):
                        text += f"• **{item}**\n"
                    # Kalau itemnya object (e.g. [{"name": "Dragon", "price": 5000000}])
                    elif isinstance(item, dict):
                        name = item.get('name', item.get('fruit', 'Unknown'))
                        price = item.get('price', item.get('value', ''))
                        text += f"• **{name}**" + (f" - 💰 {price:,} Beli\n" if price else "\n")
                
                embed.description = text if text else "```\nCould not parse stock list.\n```"

        # Kalau datanya berupa object dict:
        elif isinstance(stock_data, dict):
            # Coba cari key yang isinya array stock
            stock_key = None
            for key in ['stock', 'fruits', 'data', 'items']:
                if key in stock_data and isinstance(stock_data[key], list):
                    stock_key = key
                    break
            
            if stock_key:
                # Re-call formatter for the list inside the dict
                inner_list = stock_data[stock_key]
                text = ""
                for item in inner_list:
                    if isinstance(item, str):
                        text += f"• **{item}**\n"
                    elif isinstance(item, dict):
                        name = item.get('name', item.get('fruit', 'Unknown'))
                        price = item.get('price', item.get('value', ''))
                        text += f"• **{name}**" + (f" - 💰 {price:,} Beli\n" if price else "\n")
                embed.description = text if text else "```\nEmpty stock list.\n```"
            else:
                # Fallback: dump raw JSON biar lu bisa liat strukturnya
                raw_json = json.dumps(stock_data, indent=2)
                embed.description = f"```json\n{raw_json[:1000]}\n```"

        embed.set_footer(text="Source: blox-fruits-api | Auto-updates periodically")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BloxStock(bot))
