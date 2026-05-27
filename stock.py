import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import os
import asyncio

from ai import get_item_info  # 🔥 CONNECT TO AI

STOCK_FILE = "stock.json"


# =========================
# DATA
# =========================
def load_stock():
    if not os.path.exists(STOCK_FILE):
        return {}
    with open(STOCK_FILE, "r") as f:
        return json.load(f)


def save_stock(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# STOCK MODAL (WITH AI)
# =========================
class StockModal(Modal, title="Input Stock"):
    stock_input = TextInput(
        label="Enter Item Name",
        placeholder="dragon sword, shadow fruit",
        style=discord.TextStyle.paragraph
    )

    def __init__(self, user_id):
        super().__init__()
        self.user_id = str(user_id)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        data = load_stock()
        items = [i.strip() for i in self.stock_input.value.split(",") if i.strip()]

        if self.user_id not in data:
            data[self.user_id] = []

        added_items = []

        for item in items:
            try:
                info = await get_item_info(item)  # 🔥 AI CALL

                item_data = {
                    "name": item,
                    "rarity": info.get("rarity", "Unknown"),
                    "price": info.get("price", "Unknown")
                }

                data[self.user_id].append(item_data)
                added_items.append(item_data)

            except Exception as e:
                added_items.append({
                    "name": item,
                    "rarity": "Error",
                    "price": "Error"
                })

        save_stock(data)

        result = "\n".join([
            f"{i['name']} | {i['rarity']} | {i['price']}"
            for i in added_items
        ])

        await interaction.followup.send(
            f"✅ Added:\n```{result}```",
            ephemeral=True
        )


# =========================
# TIMER MODAL
# =========================
class TimerModal(Modal, title="Set Timer"):
    duration = TextInput(
        label="Timer (seconds)",
        placeholder="60"
    )

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            seconds = int(self.duration.value)
        except:
            return await interaction.response.send_message("❌ Invalid number", ephemeral=True)

        await interaction.response.send_message(
            f"⏳ Timer started: {seconds}s",
            ephemeral=True
        )

        await asyncio.sleep(seconds)

        await interaction.followup.send(f"⏰ Time's up <@{self.user_id}>!")


# =========================
# VIEW
# =========================
class StockView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Input Stock", style=discord.ButtonStyle.green)
    async def input_stock(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StockModal(interaction.user.id))

    @discord.ui.button(label="View Stock", style=discord.ButtonStyle.blurple)
    async def view_stock(self, interaction: discord.Interaction, button: Button):
        data = load_stock()
        user_id = str(interaction.user.id)

        if user_id not in data or not data[user_id]:
            return await interaction.response.send_message("❌ No stock", ephemeral=True)

        stock_list = "\n".join([
            f"{i['name']} | {i['rarity']} | {i['price']}"
            for i in data[user_id][:20]
        ])

        await interaction.response.send_message(
            f"📦 Stock:\n```{stock_list}```",
            ephemeral=True
        )

    @discord.ui.button(label="Clear Stock", style=discord.ButtonStyle.red)
    async def clear_stock(self, interaction: discord.Interaction, button: Button):
        data = load_stock()
        data[str(interaction.user.id)] = []
        save_stock(data)

        await interaction.response.send_message("🗑️ Cleared", ephemeral=True)

    @discord.ui.button(label="Set Timer", style=discord.ButtonStyle.gray)
    async def set_timer(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TimerModal(interaction.user.id))


# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stock(self, ctx):
        embed = discord.Embed(
            title="📦 Stock System",
            description="Input item → auto detect rarity & price",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed, view=StockView())


async def setup(bot):
    await bot.add_cog(Stock(bot))
