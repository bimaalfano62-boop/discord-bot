import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import asyncio
import json
import time
import re

STOCK_FILE = "stock.json"
PERM_FILE = "permissions.json"

# =========================
# FRUIT DATABASE
# =========================
FRUIT_DATA = {
    "pteranodon": {"rarity": "Mythical",  "emoji": "<:pter2:1509927019629121629>"},
    "dragon":     {"rarity": "Legendary", "emoji": "<:dragon:1509933316571140196>"},
    "phoenix":    {"rarity": "Legendary", "emoji": "<:phoenix:1509933208320606270>"},
    "dough":      {"rarity": "Legendary", "emoji": "<:dough:1509933266239619102>"},
    "toy":        {"rarity": "Legendary", "emoji": "<:toy:1509933247881285683>"},
    "demon":      {"rarity": "Legendary", "emoji": "<:demon:1509933300335251557>"},
    "gate":       {"rarity": "Legendary", "emoji": "<:gate:1509933228507795466>"},
    "melody":     {"rarity": "Legendary", "emoji": "<:melody:1509933284300423308>"},
    "tree":       {"rarity": "Legendary", "emoji": "<:tree:1509933333336031343>"},

    "magma":   {"rarity": "Epic", "emoji": "<:magma:1509929630734221533>"},
    "flame":   {"rarity": "Epic", "emoji": "<:flame:1509929613797883985>"},
    "light":   {"rarity": "Epic", "emoji": "<:light:1509932593926115469>"},
    "rumble":  {"rarity": "Epic", "emoji": "<:rumble:1509932833060290681>"},
    "quake":   {"rarity": "Epic", "emoji": "<:quake:1509932765783654450>"},
    "snow":    {"rarity": "Epic", "emoji": "<:snow:1509932665279746211>"},
    "gas":     {"rarity": "Epic", "emoji": "<:gas:1509932694241284167>"},
    "ice":     {"rarity": "Epic", "emoji": "<:ice:1509932635982397450>"},
    "spirit":  {"rarity": "Epic", "emoji": "<:spirit:1509932859702513685>"},
    "magnet":  {"rarity": "Epic", "emoji": "<:magnet:1509932723375050812>"},

    "leopard":  {"rarity": "Rare", "emoji": "<:leopard:1509933113055383703>"},
    "buddha":   {"rarity": "Rare", "emoji": "<:buddha:1509933037100470333>"},
    "dark":     {"rarity": "Rare", "emoji": "<:dark:1509933005374750862>"},
    "venom":    {"rarity": "Rare", "emoji": "<:venom:1509933141056422069>"},
    "control":  {"rarity": "Rare", "emoji": "<:control:1509933189089591346>"},
    "gravity":  {"rarity": "Rare", "emoji": "<:gravity:1509933161771962571>"},
    "rubber":   {"rarity": "Rare", "emoji": "<:rubber:1509932936978235512>"},
    "mammoth":  {"rarity": "Rare", "emoji": "<:mammoth:1509933080100475101>"},
    "allo":     {"rarity": "Rare", "emoji": "🦖"},
    "brachio":  {"rarity": "Rare", "emoji": "🦕"},
    "spino":    {"rarity": "Rare", "emoji": "🦎"},
    "palm":     {"rarity": "Rare", "emoji": "🌴"},

    "shadow":      {"rarity": "Uncommon", "emoji": "<:shadow:1509929594969395303>"},
    "giraffe":     {"rarity": "Uncommon", "emoji": "<:giraffe:1509929577064169542>"},
    "wolf":        {"rarity": "Uncommon", "emoji": "<:wolf:1509929559678783638>"},
    "barrier":     {"rarity": "Uncommon", "emoji": "<:barrier:1509929468364329061>"},
    "string":      {"rarity": "Uncommon", "emoji": "<:string:1509929524689768599>"},
    "telekinesis": {"rarity": "Uncommon", "emoji": "🔮"},
    "sand":        {"rarity": "Uncommon", "emoji": "<:sand:1509932967278153752>"},

    "bomb":  {"rarity": "Common", "emoji": "<:bomb:1509926839483764967>"},
    "spike": {"rarity": "Common", "emoji": "<:spike:1509927513025937408>"},
    "spin":  {"rarity": "Common", "emoji": "<:spin:1509927644009992263>"},
    "smoke": {"rarity": "Common", "emoji": "<:smoke:1509929541219647583>"},
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
# PERMISSION UTILS
# =========================
def load_perms():
    try:
        with open(PERM_FILE, "r") as f:
            return json.load(f)
    except:
        return {"allowed_users": []}

def save_perms(data):
    with open(PERM_FILE, "w") as f:
        json.dump(data, f, indent=4)

def has_stock_perm(user_id: int) -> bool:
    perms = load_perms()
    return user_id in perms["allowed_users"]

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
        return {"fruits": [], "reset_time": 0, "channel_id": None, "message_id": None, "notified": False}

def save_data(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_timer_emoji(guild: discord.Guild) -> str:
    """Use animated timer if server has boost level 1+ (allows animated emoji), else static clock."""
    if guild and guild.premium_tier >= 1:
        return "<a:timer:1509939351126016173>"
    return "⏱️"

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
    lines = []
    current_rarity = None
    for rarity in RARITY_ORDER:
        rarity_fruits = [f for f in fruits if FRUIT_DATA[f]["rarity"] == rarity]
        if not rarity_fruits:
            continue
        for f in rarity_fruits:
            lines.append(
                f"{FRUIT_DATA[f]['emoji']} **{f.capitalize()}** {RARITY_EMOJI[rarity]} `{rarity}`"
            )
    return "\n".join(lines)

def format_remaining(sec):
    if sec <= 0:
        return "Expired"
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

def build_embed(fruits, remaining, guild: discord.Guild = None):
    timer_emoji = get_timer_emoji(guild)
    color = get_embed_color(fruits) if fruits else 0x2B2D31

    embed = discord.Embed(
        title="🍇 Current Fruit Stock",
        color=color
    )

    if fruits:
        embed.description = format_fruits(fruits)
    else:
        embed.description = "```\nNo fruits in stock.\n```"

    embed.add_field(
        name=f"{timer_emoji} Resets In",
        value=f"```\n{format_remaining(remaining)}\n```",
        inline=True
    )
    embed.add_field(
        name="🍈 Total Fruits",
        value=f"```\n{len(fruits)}\n```",
        inline=True
    )
    embed.set_footer(text="Auto-updates every 5s • Blox Fruits Stock")
    return embed

# =========================
# VIEW (AUTO-UPDATE, NO BUTTON)
# =========================
class StockView(View):
    def __init__(self):
        super().__init__(timeout=None)

# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_timer.start()

    # ── Permission check helper ──
    def is_permitted(self, ctx_or_interaction):
        if isinstance(ctx_or_interaction, discord.Interaction):
            user = ctx_or_interaction.user
        else:
            user = ctx_or_interaction.author
        if user.guild_permissions.administrator:
            return True
        return has_stock_perm(user.id)

    # =========================
    # /perm SLASH COMMAND
    # =========================
    @discord.app_commands.command(name="perm", description="Grant or revoke stock management permission for a user.")
    @discord.app_commands.describe(
        action="grant or revoke",
        user="The user to grant/revoke permission"
    )
    @discord.app_commands.choices(action=[
        discord.app_commands.Choice(name="grant", value="grant"),
        discord.app_commands.Choice(name="revoke", value="revoke"),
    ])
    @discord.app_commands.default_permissions(administrator=True)
    async def perm(self, interaction: discord.Interaction, action: str, user: discord.Member):
        perms = load_perms()

        if action == "grant":
            if user.id in perms["allowed_users"]:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} already has stock permission.", ephemeral=True
                )
                return
            perms["allowed_users"].append(user.id)
            save_perms(perms)
            embed = discord.Embed(
                title="✅ Permission Granted",
                description=f"{user.mention} can now manage stock.",
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "revoke":
            if user.id not in perms["allowed_users"]:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} doesn't have stock permission.", ephemeral=True
                )
                return
            perms["allowed_users"].remove(user.id)
            save_perms(perms)
            embed = discord.Embed(
                title="🚫 Permission Revoked",
                description=f"{user.mention} can no longer manage stock.",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # =========================
    # !addstock COMMAND
    # =========================
    @commands.command()
    async def addstock(self, ctx, *, fruits: str):
        if not self.is_permitted(ctx):
            embed = discord.Embed(
                title="🚫 No Permission",
                description="You don't have permission to manage stock.",
                color=0xE74C3C
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        data = load_data()
        inputs = [f.strip() for f in fruits.split(",")]
        valid = [match_fruit(f) for f in inputs if match_fruit(f)]
        invalid = [f for f in inputs if not match_fruit(f)]

        if not valid:
            embed = discord.Embed(
                title="❌ Invalid Fruits",
                description="None of the fruits you entered are valid.",
                color=0xE74C3C
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        # Ask for timer
        prompt = discord.Embed(
            title="⏳ Set Timer",
            description="How long until stock resets?\n\nExamples: `1h 30m` · `90m` · `3600s`",
            color=0x5865F2
        )
        if invalid:
            prompt.set_footer(text=f"Ignored invalid: {', '.join(invalid)}")
        await ctx.send(embed=prompt)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Timed out. Run `!addstock` again.", delete_after=5)
            return

        seconds = parse_time(msg.content)
        if seconds <= 0:
            await ctx.send("❌ Invalid time format.", delete_after=5)
            return

        # Delete old stock message if exists
        if data.get("channel_id") and data.get("message_id"):
            try:
                old_channel = self.bot.get_channel(data["channel_id"])
                old_msg = await old_channel.fetch_message(data["message_id"])
                await old_msg.delete()
            except:
                pass

        data["fruits"] = valid
        data["channel_id"] = ctx.channel.id
        data["reset_time"] = int(time.time()) + seconds
        data["notified"] = False

        sent = await ctx.send(
            embed=build_embed(valid, seconds, ctx.guild),
            view=StockView()
        )
        data["message_id"] = sent.id
        save_data(data)

    # =========================
    # !stock COMMAND
    # =========================
    @commands.command()
    async def stock(self, ctx):
        data = load_data()
        remaining = data["reset_time"] - int(time.time())

        if not data["fruits"] or remaining <= 0:
            embed = discord.Embed(
                title="❌ No Active Stock",
                description="There is currently no active stock.",
                color=0x2B2D31
            )
            await ctx.send(embed=embed, delete_after=8)
            return

        sent = await ctx.send(
            embed=build_embed(data["fruits"], remaining, ctx.guild),
            view=StockView()
        )
        # Track this new message for auto-update
        data["channel_id"] = ctx.channel.id
        data["message_id"] = sent.id
        save_data(data)

    # =========================
    # !howstock COMMAND
    # =========================
    @commands.command()
    async def howstock(self, ctx):
        embed = discord.Embed(
            title="📘 How to Use Stock Bot",
            color=0x5865F2
        )
        embed.add_field(
            name="1️⃣ Add Stock",
            value="`!addstock dragon, dough, flame`",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Set Timer",
            value="`1h 30m` · `90m` · `3600s`",
            inline=False
        )
        embed.add_field(
            name="3️⃣ View Stock",
            value="`!stock`",
            inline=False
        )
        embed.add_field(
            name="⚙️ System",
            value="• Auto countdown (updates every 5s)\n• 1 min warning\n• Auto reset on expire",
            inline=False
        )
        embed.add_field(
            name="🔐 Permissions",
            value="Admins can grant access with `/perm grant @user`",
            inline=False
        )
        embed.set_footer(text="Separate fruits with commas!")
        await ctx.send(embed=embed)

    # =========================
    # AUTO-UPDATE LOOP
    # =========================
    @tasks.loop(seconds=5)
    async def check_timer(self):
        data = load_data()

        if not data.get("channel_id") or not data.get("message_id"):
            return

        remaining = data["reset_time"] - int(time.time())
        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return

        # Auto-edit the stock message every 5s
        if data["fruits"] and remaining > 0:
            try:
                msg = await channel.fetch_message(data["message_id"])
                guild = channel.guild
                await msg.edit(embed=build_embed(data["fruits"], remaining, guild))
            except:
                pass

        # 1-minute warning
        if remaining <= 60 and remaining > 0 and not data["notified"]:
            await channel.send("⚠️ Stock resets in **1 minute!**")
            data["notified"] = True
            save_data(data)

        # Expired
        if remaining <= 0 and data["fruits"]:
            try:
                msg = await channel.fetch_message(data["message_id"])
                expired_embed = discord.Embed(
                    title="🔄 Stock Expired",
                    description="Stock has been reset. Waiting for new stock...",
                    color=0x2B2D31
                )
                expired_embed.set_footer(text="Blox Fruits Stock")
                await msg.edit(embed=expired_embed, view=None)
            except:
                pass

            data["fruits"] = []
            data["reset_time"] = 0
            data["notified"] = False
            data["message_id"] = None
            save_data(data)
            await channel.send("🔄 **Stock has been reset!**")

    @check_timer.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Stock(bot))
