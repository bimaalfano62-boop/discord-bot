import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
import requests
from bs4 import BeautifulSoup

# ================= SCRAPER =================
def fetch_fruits():
    url = "https://king-legacy-official.fandom.com/wiki/Legacy_Fruits"
    res = requests.get(url)

    fruits = {}

    if res.status_code != 200:
        print("❌ Failed to fetch wiki")
        return fruits

    soup = BeautifulSoup(res.text, "html.parser")
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")[1:]

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            name = cols[0].text.strip()
            rarity = cols[1].text.strip()
            price = cols[2].text.strip()

            if name:
                fruits[name] = {
                    "rarity": rarity,
                    "price": price
                }

    print(f"✅ Loaded {len(fruits)} fruits")
    return fruits


FRUITS = fetch_fruits()

# ================= COG =================
class StockCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stock = {}

        # ✅ FIX TIMER SYSTEM
        self.default_timer = 60
        self.timer = self.default_timer

        self.reset_task.start()

    def cog_unload(self):
        self.reset_task.cancel()

    # ================= GLOBAL TIMER =================
    @tasks.loop(minutes=1)
    async def reset_task(self):
        self.timer -= 1

        if self.timer <= 0:
            self.stock.clear()
            print("🔥 STOCK RESET")

            # reset to last set timer
            self.timer = self.default_timer

    # ================= UI =================
    class MainView(View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="➕ Input Stock", style=discord.ButtonStyle.green)
        async def input_stock(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message(
                "Select fruit:",
                view=StockCog.FruitSelect(self.cog),
                ephemeral=True
            )

        @discord.ui.button(label="⏱ Set Timer", style=discord.ButtonStyle.blurple)
        async def set_timer(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_modal(StockCog.TimerModal(self.cog))

        @discord.ui.button(label="📦 View Stock", style=discord.ButtonStyle.gray)
        async def view_stock(self, interaction: discord.Interaction, button: Button):
            if not self.cog.stock:
                return await interaction.response.send_message("Stock is empty", ephemeral=True)

            msg = ""
            for fruit, qty in self.cog.stock.items():
                data = FRUITS.get(fruit, {})
                msg += f"**{fruit}** | {data.get('rarity')} | {data.get('price')} | Qty: {qty}\n"

            msg += f"\n⏱ Reset in: {self.cog.timer} min"

            await interaction.response.send_message(msg, ephemeral=True)

    # ================= SELECT =================
    class FruitSelect(View):
        def __init__(self, cog):
            super().__init__(timeout=60)
            self.cog = cog

            fruit_names = list(FRUITS.keys())

            options = [
                discord.SelectOption(label=name[:100])
                for name in fruit_names[:25]  # discord limit
            ]

            self.add_item(StockCog.FruitDropdown(cog, options))

    class FruitDropdown(Select):
        def __init__(self, cog, options):
            super().__init__(placeholder="Choose fruit", options=options)
            self.cog = cog

        async def callback(self, interaction: discord.Interaction):
            fruit = self.values[0]
            await interaction.response.send_modal(StockCog.StockModal(self.cog, fruit))

    # ================= MODAL =================
    class StockModal(Modal, title="Input Stock"):
        def __init__(self, cog, fruit):
            super().__init__()
            self.cog = cog
            self.fruit = fruit

            self.amount = TextInput(label="Amount", placeholder="example: 5")
            self.add_item(self.amount)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                qty = int(self.amount.value)
                self.cog.stock[self.fruit] = qty

                await interaction.response.send_message(
                    f"✅ {self.fruit} = {qty}",
                    ephemeral=True
                )
            except:
                await interaction.response.send_message("❌ Must be a number", ephemeral=True)

    class TimerModal(Modal, title="Set Timer (minutes)"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog

            self.time = TextInput(label="Minutes", placeholder="example: 30")
            self.add_item(self.time)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                new_time = int(self.time.value)

                self.cog.timer = new_time
                self.cog.default_timer = new_time  # ✅ IMPORTANT

                await interaction.response.send_message(
                    f"⏱ Timer set to {new_time} minutes",
                    ephemeral=True
                )
            except:
                await interaction.response.send_message("❌ Must be a number", ephemeral=True)

    # ================= COMMAND =================
    @commands.command()
    async def stock(self, ctx):
        await ctx.send("📊 Stock Dashboard", view=self.MainView(self))


# ================= SETUP =================
async def setup(bot):
    await bot.add_cog(StockCog(bot))
