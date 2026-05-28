import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import asyncio
import json
import time
import re

STOCK_FILE = "stock.json"

# =========================
# FRUIT DATABASE
# =========================
FRUIT_DATA = {
    # Mythical
    "pteranodon": {"rarity": "Mythical",  "emoji": "🦕"},
    # Legendary
    "dragon":  {"rarity": "Legendary", "emoji": "🐉"},
    "phoenix": {"rarity": "Legendary", "emoji": "🦅"},
    "dough":   {"rarity": "Legendary", "emoji": "🍞"},
    "toy":     {"rarity": "Legendary", "emoji": "🧸"},
    "demon":   {"rarity": "Legendary", "emoji": "😈"},
    "gate":    {"rarity": "Legendary", "emoji": "🚪"},
    "melody":  {"rarity": "Legendary", "emoji": "🎵"},
    "tree":    {"rarity": "Legendary", "emoji": "🌳"},
    # Epic
    "magma":   {"rarity": "Epic", "emoji": "🌋"},
    "flame":   {"rarity": "Epic", "emoji": "🔥"},
    "light":   {"rarity": "Epic", "emoji": "💡"},
    "rumble":  {"rarity": "Epic", "emoji": "⚡"},
    "quake":   {"rarity": "Epic", "emoji": "💥"},
    "snow":    {"rarity": "Epic", "emoji": "❄️"},
    "gas":     {"rarity": "Epic", "emoji": "💀"},
    "ice":     {"rarity": "Epic", "emoji": "🧊"},
    "spirit":  {"rarity": "Epic", "emoji": "👻"},
    "magnet":  {"rarity": "Epic", "emoji": "🧲"},
    # Rare
    "leopard":  {"rarity": "Rare", "emoji": "🐆"},
    "buddha":   {"rarity": "Rare", "emoji": "☯️"},
    "dark":     {"rarity": "Rare", "emoji": "🌙"},
    "venom":    {"rarity": "Rare", "emoji": "☠️"},
    "control":  {"rarity": "Rare", "emoji": "🌀"},
    "gravity":  {"rarity": "Rare", "emoji": "🌍"},
    "rubber":   {"rarity": "Rare", "emoji": "🫧"},
    "mammoth":  {"rarity": "Rare", "emoji": "🦣"},
    "allo":     {"rarity": "Rare", "emoji": "🦖"},
    "brachio":  {"rarity": "Rare", "emoji": "🦕"},
    "spino":    {"rarity": "Rare", "emoji": "🦎"},
    "palm":     {"rarity": "Rare", "emoji": "🌴"},
    # Uncommon
    "shadow":      {"rarity": "Uncommon", "emoji": "🌑"},
    "giraffe":     {"rarity": "Uncommon", "emoji": "🦒"},
    "wolf":        {"rarity": "Uncommon", "emoji": "🐺"},
    "barrier":     {"rarity": "Uncommon", "emoji": "🛡️"},
    "string":      {"rarity": "Uncommon", "emoji": "🧵"},
    "telekinesis": {"rarity": "Uncommon", "emoji": "🔮"},
    "sand":        {"rarity": "Uncommon", "emoji": "🏜️"},
    # Common
    "bomb":  {"rarity": "Common", "emoji": "💣"},
    "spike": {"rarity": "Common", "emoji": "🗡️"},
    "spin":  {"rarity": "Common", "emoji": "🌀"},
    "smoke": {"rarity": "Common", "emoji": "💨"},
}

RARITY_ORDER = ["Mythical", "Legendary", "Epic", "Rare", "Uncommon", "Common"]

RARITY_COLORS = {
    "Mythical":  0xFF0000,
    "Legendary": 0xFFD700,
    "Epic":      0x9B59B6,
    "Rare":      0x3498DB,
    "Uncommon":  0x2ECC71,
    "Common":    0x95A5A6,
}

RARITY_EMOJI = {
    "Mythical":  "🔴",
    "Legendary": "🟡",
    "Epic":      "🟣",
    "Rare":      "🔵",
    "Uncommon":  "🟢",
    "Common":    "⚪",
}

# =========================
# FRUIT LOOKUP
# =========================
def match_fruit(input_name: str):
    key = input_name.lower().strip()
    if key in FRUIT_DATA:
        return key
    return None

def get_embed_color(fruits: list) -> int:
    for rarity in RARITY_ORDER:
        for fruit in fruits:
            if FRUIT_DATA[fruit]["rarity"] == rarity:
                return RARITY_COLORS[rarity]
    return 0x5865F2

# =========================
# LOAD & SAVE
# =========================
def load_data():
    try:
        with open(STOCK_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "fruits": [],
            "reset_time": 0,
            "channel_id": None,
            "notified": False
        }

def save_data(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# PARSE TIMER
# =========================
def parse_time(time_str: str) -> int:
    time_str = time_str.lower()
    hours = minutes = seconds = 0

    h = re.findall(r'(\d+)\s*(hours|hour|hrs|hr|h)', time_str)
    m = re.findall(r'(\d+)\s*(minutes|minute|mins|min|m)', time_str)
    s = re.findall(r'(\d+)\s*(seconds|second|secs|sec|s)', time_str)

    if h: hours = int(h[0][0])
    if m: minutes = int(m[0][0])
    if s: seconds = int(s[0][0])

    if not (h or m or s):
        try:
            minutes = int(time_str.strip())
        except:
            pass

    return hours * 3600 + minutes * 60 + seconds

# =========================
# FORMAT HELPERS
# =========================
def format_fruits(fruits: list) -> str:
    result = []
    for fruit in fruits:
        d = FRUIT_DATA[fruit]
        r_emoji = RARITY_EMOJI[d["rarity"]]
        result.append(f"{d['emoji']} **{fruit.capitalize()}** {r_emoji} `{d['rarity']}`")
    return "\n".join(result)

def format_remaining(remaining: int) -> str:
    remaining = max(0, remaining)
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    seconds = remaining % 60
    parts = []
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"

def build_stock_embed(fruits: list, remaining: int) -> discord.Embed:
    embed = discord.Embed(
        title="🍇 King Legacy — Current Stock",
        description=format_fruits(fruits),
        color=get_embed_color(fruits)
    )
    embed.add_field(name="⏳ Reset In", value=f"`{format_remaining(remaining)}`", inline=True)
    embed.add_field(name="🍈 Total",    value=f"`{len(fruits)} fruit`",           inline=True)
    embed.set_footer(text="King Legacy Stock Bot • Auto resets when timer hits 0")
    return embed

# =========================
# STOCK VIEW (BUTTONS)
# =========================
class StockView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["fruits"]:
            await interaction.response.send_message("❌ No stock available.", ephemeral=True)
            return
        remaining = data["reset_time"] - int(time.time())
        if remaining <= 0:
            await interaction.response.send_message("⚠️ Stock has expired.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=build_stock_embed(data["fruits"], remaining), view=self
        )

    @discord.ui.button(label="Time Left", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def time_left(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        remaining = data["reset_time"] - int(time.time())
        if remaining <= 0:
            await interaction.response.send_message("⚠️ Stock has expired.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"⏳ Stock resets in **{format_remaining(remaining)}**", ephemeral=True
            )

    @discord.ui.button(label="List Fruits", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_fruits(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["fruits"]:
            await interaction.response.send_message("❌ No stock available.", ephemeral=True)
            return
        lines = [
            f"• {FRUIT_DATA[f]['emoji']} {f.capitalize()} — `{FRUIT_DATA[f]['rarity']}`"
            for f in data["fruits"]
        ]
        await interaction.response.send_message(
            "📋 **Fruits in stock:**\n" + "\n".join(lines), ephemeral=True
        )

# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_timer.start()

    def cog_unload(self):
        self.check_timer.cancel()

    # =========================
    # ADD STOCK
    # =========================
    @commands.command()
    async def addstock(self, ctx, *, raw_input: str = None):
        data = load_data()

        if raw_input:
            inputs = [f.strip() for f in raw_input.split(",")]
        else:
            await ctx.send("🍇 Send fruit names separated by commas\nExample: `Dragon, Dough, Tree`")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                msg = await self.bot.wait_for("message", timeout=60, check=check)
                inputs = [f.strip() for f in msg.content.split(",")]
            except asyncio.TimeoutError:
                await ctx.send("❌ Timed out, please try again.")
                return

        valid, invalid = [], []
        for name in inputs:
            matched = match_fruit(name)
            if matched:
                valid.append(matched)
            else:
                invalid.append(name)

        if invalid:
            await ctx.send(
                f"⚠️ The following fruits were **not found** in the database:\n"
                f"`{'`, `'.join(invalid)}`\n"
                f"Use `!fruitlist` to see all available fruits."
            )

        if not valid:
            await ctx.send("❌ No valid fruits to add.")
            return

        data["fruits"] = valid
        data["channel_id"] = ctx.channel.id

        await ctx.send("⏳ Send the timer\nExample: `6h` / `1hour 30m` / `1h 2m 3s`")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg2 = await self.bot.wait_for("message", timeout=60, check=check)
            total_seconds = parse_time(msg2.content)
            if total_seconds <= 0:
                await ctx.send("❌ Invalid timer.")
                return
            data["reset_time"] = int(time.time()) + total_seconds
            data["notified"] = False
            save_data(data)

            embed = build_stock_embed(valid, total_seconds)
            embed.title = "✅ Stock Updated! — King Legacy"
            await ctx.send(embed=embed, view=StockView(self.bot))

        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out, please try again.")

    # =========================
    # SHOW STOCK
    # =========================
    @commands.command()
    async def stock(self, ctx):
        data = load_data()
        if not data["fruits"]:
            await ctx.send("❌ No stock available.")
            return
        remaining = data["reset_time"] - int(time.time())
        if remaining <= 0:
            await ctx.send("⚠️ Stock has expired.")
            return
        await ctx.send(embed=build_stock_embed(data["fruits"], remaining), view=StockView(self.bot))

    @commands.command()
    async def viewstock(self, ctx):
        await ctx.invoke(self.bot.get_command("stock"))

    # =========================
    # SET TIMER
    # =========================
    @commands.command()
    async def settimer(self, ctx, *, time_str: str = None):
        data = load_data()
        if not data["fruits"]:
            await ctx.send("❌ No stock available. Use `!addstock` first.")
            return

        if not time_str:
            await ctx.send("⏳ Send the new timer\nExample: `6h` / `1hour 30mins` / `1h 2m 3s`")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                msg = await self.bot.wait_for("message", timeout=60, check=check)
                time_str = msg.content
            except asyncio.TimeoutError:
                await ctx.send("❌ Timed out, please try again.")
                return

        total_seconds = parse_time(time_str)
        if total_seconds <= 0:
            await ctx.send("❌ Invalid timer.")
            return

        data["reset_time"] = int(time.time()) + total_seconds
        data["notified"] = False
        save_data(data)

        embed = build_stock_embed(data["fruits"], total_seconds)
        embed.title = "⏱️ Timer Updated! — King Legacy"
        await ctx.send(embed=embed, view=StockView(self.bot))

    # =========================
    # FRUIT LIST
    # =========================
    @commands.command()
    async def fruitlist(self, ctx):
        embed = discord.Embed(title="📖 King Legacy Fruit Database", color=0x5865F2)
        for rarity in RARITY_ORDER:
            fruits_in_rarity = [
                f"{v['emoji']} {k.capitalize()}"
                for k, v in FRUIT_DATA.items()
                if v["rarity"] == rarity
            ]
            if fruits_in_rarity:
                embed.add_field(
                    name=f"{RARITY_EMOJI[rarity]} {rarity}",
                    value="\n".join(fruits_in_rarity),
                    inline=True
                )
        await ctx.send(embed=embed)

    # =========================
    # HOW TO USE
    # =========================
    @commands.command()
    async def howstock(self, ctx):
        embed = discord.Embed(title="📘 Stock Bot — How to Use", color=0x5865F2)
        embed.add_field(
            name="`!addstock`",
            value="Direct: `!addstock Dragon, Dough, Tree`\nOr type without arguments and follow the prompts",
            inline=False
        )
        embed.add_field(
            name="`!stock` / `!viewstock`",
            value="View current stock + countdown + buttons",
            inline=False
        )
        embed.add_field(
            name="`!settimer`",
            value="Change the timer without changing the stock\nExample: `!settimer 1hour 30m` / `!settimer 6h`",
            inline=False
        )
        embed.add_field(name="`!fruitlist`", value="View all fruits in the database with their rarity", inline=False)
        embed.add_field(
            name="⚙️ Timer Format",
            value="`6h` • `1hour 30m` • `1h 2m 3s` • `1hours 2mins 3secs` • `30` (minutes)",
            inline=False
        )
        await ctx.send(embed=embed)

    # =========================
    # TIMER LOOP
    # =========================
    @tasks.loop(seconds=5)
    async def check_timer(self):
        data = load_data()
        if data["reset_time"] == 0 or not data["channel_id"]:
            return

        now = int(time.time())
        remaining = data["reset_time"] - now
        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return

        if remaining <= 60 and remaining > 0 and not data.get("notified"):
            await channel.send("⚠️ Stock will reset in **1 minute!**")
            data["notified"] = True
            save_data(data)

        if remaining <= 0:
            data["fruits"] = []
            data["reset_time"] = 0
            data["notified"] = False
            save_data(data)
            await channel.send("🔄 Stock has been reset! Use `!addstock` to set new stock.")

    @check_timer.before_loop
    async def before_timer(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Stock(bot))
