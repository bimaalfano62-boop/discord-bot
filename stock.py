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
    "pteranodon": {"rarity": "Mythical",  "emoji": "🦕"},
    "dragon":  {"rarity": "Legendary", "emoji": "🐉"},
    "phoenix": {"rarity": "Legendary", "emoji": "🦅"},
    "dough":   {"rarity": "Legendary", "emoji": "🍞"},
    "toy":     {"rarity": "Legendary", "emoji": "🧸"},
    "demon":   {"rarity": "Legendary", "emoji": "😈"},
    "gate":    {"rarity": "Legendary", "emoji": "🚪"},
    "melody":  {"rarity": "Legendary", "emoji": "🎵"},
    "tree":    {"rarity": "Legendary", "emoji": "🌳"},

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

    "shadow":      {"rarity": "Uncommon", "emoji": "🌑"},
    "giraffe":     {"rarity": "Uncommon", "emoji": "🦒"},
    "wolf":        {"rarity": "Uncommon", "emoji": "🐺"},
    "barrier":     {"rarity": "Uncommon", "emoji": "🛡️"},
    "string":      {"rarity": "Uncommon", "emoji": "🧵"},
    "telekinesis": {"rarity": "Uncommon", "emoji": "🔮"},
    "sand":        {"rarity": "Uncommon", "emoji": "🏜️"},

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
# UTILS
# =========================
def match_fruit(input_name: str):
    key = input_name.lower().strip()
    return key if key in FRUIT_DATA else None

def get_embed_color(fruits):
    for rarity in RARITY_ORDER:
        for fruit in fruits:
            if FRUIT_DATA[fruit]["rarity"] == rarity:
                return RARITY_COLORS[rarity]
    return 0x5865F2

def load_data():
    try:
        with open(STOCK_FILE, "r") as f:
            return json.load(f)
    except:
        return {"fruits": [], "reset_time": 0, "channel_id": None, "notified": False}

def save_data(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# TIMER PARSER
# =========================
def parse_time(time_str):
    time_str = time_str.lower()
    h = re.findall(r'(\d+)h', time_str)
    m = re.findall(r'(\d+)m', time_str)
    s = re.findall(r'(\d+)s', time_str)

    hours = int(h[0]) if h else 0
    minutes = int(m[0]) if m else 0
    seconds = int(s[0]) if s else 0

    if not (h or m or s):
        try:
            minutes = int(time_str)
        except:
            return 0

    return hours * 3600 + minutes * 60 + seconds

# =========================
# FORMAT
# =========================
def format_fruits(fruits):
    return "\n".join([
        f"{FRUIT_DATA[f]['emoji']} **{f.capitalize()}** {RARITY_EMOJI[FRUIT_DATA[f]['rarity']]} `{FRUIT_DATA[f]['rarity']}`"
        for f in fruits
    ])

def format_remaining(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}h {m}m {s}s"

def build_embed(fruits, remaining):
    embed = discord.Embed(
        title="🍇 Current Stock",
        description=format_fruits(fruits),
        color=get_embed_color(fruits)
    )
    embed.add_field(name="⏳ Reset In", value=format_remaining(remaining))
    embed.add_field(name="🍈 Total", value=str(len(fruits)))
    return embed

# =========================
# VIEW (FIXED PUBLIC)
# =========================
class StockView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction, button):
        data = load_data()
        remaining = data["reset_time"] - int(time.time())

        if remaining <= 0:
            await interaction.response.send_message("Expired", ephemeral=False)
            return

        await interaction.response.edit_message(
            embed=build_embed(data["fruits"], remaining),
            view=self
        )

# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_timer.start()

    @commands.command()
    async def addstock(self, ctx, *, fruits: str):
        data = load_data()

        inputs = [f.strip() for f in fruits.split(",")]
        valid = [match_fruit(f) for f in inputs if match_fruit(f)]

        if not valid:
            await ctx.send("❌ No valid fruits")
            return

        data["fruits"] = valid
        data["channel_id"] = ctx.channel.id

        await ctx.send("⏳ Send timer (example: 1h 30m)")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        msg = await self.bot.wait_for("message", check=check)
        seconds = parse_time(msg.content)

        data["reset_time"] = int(time.time()) + seconds
        data["notified"] = False
        save_data(data)

        await ctx.send(
            embed=build_embed(valid, seconds),
            view=StockView(self.bot)
        )

    @commands.command()
    async def stock(self, ctx):
        data = load_data()
        remaining = data["reset_time"] - int(time.time())

        if remaining <= 0:
            await ctx.send("❌ Expired")
            return

        await ctx.send(
            embed=build_embed(data["fruits"], remaining),
            view=StockView(self.bot)
        )

    @tasks.loop(seconds=5)
    async def check_timer(self):
        data = load_data()

        if not data["channel_id"]:
            return

        remaining = data["reset_time"] - int(time.time())
        channel = self.bot.get_channel(data["channel_id"])

        if remaining <= 60 and remaining > 0 and not data["notified"]:
            await channel.send("⚠️ 1 minute left!")
            data["notified"] = True
            save_data(data)

        if remaining <= 0 and data["fruits"]:
            data["fruits"] = []
            data["reset_time"] = 0
            data["notified"] = False
            save_data(data)
            await channel.send("🔄 Stock reset!")

    @check_timer.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

@commands.command()
async def howstock(self, ctx):
    await ctx.send("""
📘 **HOW TO USE STOCK BOT**

1. Add stock:
`!addstock dragon, dough, flame`

2. Set timer:
`1h 30m` or `90m` or `3600s`

3. View stock:
`!stock`

⚙️ System:
- Auto countdown
- 1 min warning
- Auto reset

💡 Tips:
Use comma to separate fruits!
""")


async def setup(bot):
    await bot.add_cog(Stock(bot))
