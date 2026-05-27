import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import os

STOCK_FILE = "stock.json"


# =========================
# DATA HANDLER
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
# MODAL (POPUP INPUT)
# =========================
class StockModal(Modal, title="Input Stock"):
    stock_input = TextInput(
        label="Enter Stock",
        placeholder="example: acc1:pass1, acc2:pass2",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self, user_id):
        super().__init__()
        self.user_id = str(user_id)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_stock()

        items = [i.strip() for i in self.stock_input.value.split(",") if i.strip()]

        if self.user_id not in data:
            data[self.user_id] = []

        data[self.user_id].extend(items)
        save_stock(data)

        await interaction.response.send_message(
            f"✅ Successfully added **{len(items)} stock(s)**",
            ephemeral=True
        )


# =========================
# BUTTON VIEW
# =========================
class StockView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Input Stock",
        style=discord.ButtonStyle.green,
        custom_id="input_stock_btn"
    )
    async def input_stock(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(
            StockModal(interaction.user.id)
        )

    @discord.ui.button(
        label="View Stock",
        style=discord.ButtonStyle.blurple,
        custom_id="view_stock_btn"
    )
    async def view_stock(self, interaction: discord.Interaction, button: Button):
        data = load_stock()
        user_id = str(interaction.user.id)

        if user_id not in data or not data[user_id]:
            return await interaction.response.send_message(
                "❌ You don't have any stock",
                ephemeral=True
            )

        stock_list = "\n".join(data[user_id][:20])

        await interaction.response.send_message(
            f"📦 **Your Stock:**\n```{stock_list}```",
            ephemeral=True
        )

    @discord.ui.button(
        label="Clear Stock",
        style=discord.ButtonStyle.red,
        custom_id="clear_stock_btn"
    )
    async def clear_stock(self, interaction: discord.Interaction, button: Button):
        data = load_stock()
        user_id = str(interaction.user.id)

        if user_id in data:
            data[user_id] = []
            save_stock(data)

        await interaction.response.send_message(
            "🗑️ Your stock has been cleared",
            ephemeral=True
        )


# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stock(self, ctx):
        embed = discord.Embed(
            title="📦 Stock Dashboard",
            description="Manage your stock using buttons below",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed, view=StockView())


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Stock(bot))
