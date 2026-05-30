import discord
from discord.ext import commands, tasks
from discord.ui import View
import asyncio
import json
import time
import re

# =========================
# FRUIT DATABASE
# =========================
FRUIT_DATA = {
    # ── Mythical ──────────────────────────────────────────
    "pteranodon": {
        "rarity": "Mythical",
        "emoji": "<:pter2:1509927019629121629>",
        "price": 51_000_000,
    },
    # ── Legendary ─────────────────────────────────────────
    "dragon":  {"rarity": "Legendary", "emoji": "<:dragon:1509933316571140196>",  "price": 50_000_000},
    "phoenix": {"rarity": "Legendary", "emoji": "<:phoenix:1509933208320606270>", "price": 47_000_000},
    "dough":   {"rarity": "Legendary", "emoji": "<:dough:1509933266239619102>",   "price": 28_500_000},
    "toy":     {"rarity": "Legendary", "emoji": "<:toy:1509933247881285683>",     "price": 45_000_000},
    "demon":   {"rarity": "Legendary", "emoji": "<:demon:1509933300335251557>",   "price": 44_000_000},
    "gate":    {"rarity": "Legendary", "emoji": "<:gate:1509933228507795466>",    "price": 39_500_000},
    "melody":  {"rarity": "Legendary", "emoji": "<:melody:1509933284300423308>",  "price": 33_000_000},
    "tree":    {"rarity": "Legendary", "emoji": "<:tree:1509933333336031343>",    "price": 30_000_000},

    # ── Epic ──────────────────────────────────────────────
    "magma":   {"rarity": "Epic", "emoji": "<:magma:1509929630734221533>",   "price": 10_500_000},
    "flame":   {"rarity": "Epic", "emoji": "<:flame:1509929613797883985>",   "price": 11_500_000},
    "light":   {"rarity": "Epic", "emoji": "<:light:1509932593926115469>",   "price": 12_500_000},
    "rumble":  {"rarity": "Epic", "emoji": "<:rumble:1509932833060290681>",  "price": 12_250_000},
    "quake":   {"rarity": "Epic", "emoji": "<:quake:1509932765783654450>",   "price": 10_500_000},
    "snow":    {"rarity": "Epic", "emoji": "<:snow:1509932665279746211>",    "price": 10_750_000},
    "gas":     {"rarity": "Epic", "emoji": "<:gas:1509932694241284167>",     "price": 11_750_000},
    "ice":     {"rarity": "Epic", "emoji": "<:ice:1509932635982397450>",     "price": 8_100_000},
    "spirit":  {"rarity": "Epic", "emoji": "<:spirit:1509932859702513685>",  "price": 9_000_000},
    "magnet":  {"rarity": "Epic", "emoji": "<:magnet:1509932723375050812>",  "price": 11_850_000},

    # ── Rare ──────────────────────────────────────────────
    "leopard":  {"rarity": "Rare", "emoji": "<:leopard:1509933113055383703>", "price": 1_000_000},
    "buddha":   {"rarity": "Rare", "emoji": "<:buddha:1509933037100470333>",  "price": 1_950_000},
    "dark":     {"rarity": "Rare", "emoji": "<:dark:1509933005374750862>",    "price": 7_000_000},
    "venom":    {"rarity": "Rare", "emoji": "<:venom:1509933141056422069>",   "price": 1_950_000},
    "control":  {"rarity": "Rare", "emoji": "<:control:1509933189089591346>", "price": 3_500_000},
    "gravity":  {"rarity": "Rare", "emoji": "<:gravity:1509933161771962571>", "price": 2_800_000},
    "rubber":   {"rarity": "Rare", "emoji": "<:rubber:1509932936978235512>",  "price": 6_250_000},
    "mammoth":  {"rarity": "Rare", "emoji": "<:mammoth:1509933080100475101>", "price": 3_700_000},
    "allo":     {"rarity": "Rare", "emoji": "<:allo:1509940707908124905>",                             "price": 2_800_000},
    "brachio":  {"rarity": "Rare", "emoji": "<:brachio:1509940751788937426>",                             "price": 3_000_000},
    "spino":    {"rarity": "Rare", "emoji": "<:spino:1509940730846773298>",                             "price": 6_000_000},
    "paw":     {"rarity": "Rare", "emoji": "<:paw:1509929487381299251>",                             "price": 1_500_000},

    # ── Uncommon ──────────────────────────────────────────
    "shadow":      {"rarity": "Uncommon", "emoji": "<:shadow:1509929594969395303>", "price": 4_100_000},
    "giraffe":     {"rarity": "Uncommon", "emoji": "<:giraffe:1509929577064169542>","price": 700_000},
    "wolf":        {"rarity": "Uncommon", "emoji": "<:wolf:1509929559678783638>",   "price": 700_000},
    "barrier":     {"rarity": "Uncommon", "emoji": "<:barrier:1509929468364329061>","price": 1_350_000},
    "string":      {"rarity": "Uncommon", "emoji": "<:string:1509929524689768599>", "price": 5_100_000},
    "telekinesis": {"rarity": "Uncommon", "emoji": "<:telekinesis:1509945137185161236>",                            "price": 2_750_000},
    "sand":        {"rarity": "Uncommon", "emoji": "<:sand:1509932967278153752>",   "price": 1_500_000},

    # ── Common ────────────────────────────────────────────
    "bomb":  {"rarity": "Common", "emoji": "<:bomb:1509926839483764967>",  "price": 250_000},
    "spike": {"rarity": "Common", "emoji": "<:spike:1509927513025937408>", "price": 1_300_000},
    "spin":  {"rarity": "Common", "emoji": "<:spin:1509927644009992263>",  "price": 150_000},
    "smoke": {"rarity": "Common", "emoji": "<:smoke:1509929541219647583>", "price": 2_400_000},
}

RARITY_ORDER  = ["Mythical", "Legendary", "Epic", "Rare", "Uncommon", "Common"]

RARITY_COLORS = {
    "Mythical":  0xFF0000,
    "Legendary": 0xFFD700,
    "Epic":      0x9B59B6,
    "Rare":      0x3498DB,
    "Uncommon":  0x2ECC71,
    "Common":    0x95A5A6,
}

RARITY_EMOJI = {
    "Mythical":  "<:mhytical:1510071574982561933>",
    "Legendary": "<:legendary:1510071553491075203>",
    "Epic":      "<:epic:1510071538383061153>",
    "Rare":      "<:rare:1510071597002653877>",
    "Uncommon":  "<:uncummon:1510071612114993202>",
    "Common":    "<:common:1510071627637854368>",
}

# =========================
# PER-GUILD FILE PATHS
# =========================
def stock_file(guild_id: int) -> str:
    return f"stock_{guild_id}.json"

def perm_file(guild_id: int) -> str:
    return f"perm_{guild_id}.json"

# =========================
# PERMISSION UTILS
# =========================
def load_perms(guild_id: int):
    try:
        with open(perm_file(guild_id), "r") as f:
            return json.load(f)
    except:
        return {"allowed_users": []}

def save_perms(guild_id: int, data):
    with open(perm_file(guild_id), "w") as f:
        json.dump(data, f, indent=4)

def has_stock_perm(guild_id: int, user_id: int) -> bool:
    return user_id in load_perms(guild_id)["allowed_users"]

# =========================
# STOCK DATA UTILS
# =========================
def load_data(guild_id: int):
    try:
        with open(stock_file(guild_id), "r") as f:
            return json.load(f)
    except:
        return {
            "fruits":     [],
            "reset_time": 0,
            "channel_id": None,
            "message_id": None,
            "notified":   False,
        }

def save_data(guild_id: int, data):
    with open(stock_file(guild_id), "w") as f:
        json.dump(data, f, indent=4)

# =========================
# GENERAL UTILS
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

def get_timer_emoji(guild: discord.Guild) -> str:
    if guild and guild.premium_tier >= 1:
        return "<a:timer:1509939351126016173>"
    return "⏱️"

def format_price(beli: int) -> str:
    if beli >= 1_000_000:
        s = f"{beli / 1_000_000:g}M"
    elif beli >= 1_000:
        s = f"{beli / 1_000:g}K"
    else:
        s = f"{beli:,}"
    return f"`{s}` <:money:1510067350962045018>"

# =========================
# TIMER PARSER
# =========================
def parse_time(time_str: str) -> int:
    time_str = time_str.lower()
    h = re.findall(r'(\d+)h', time_str)
    m = re.findall(r'(\d+)m', time_str)
    s = re.findall(r'(\d+)s', time_str)

    hours   = int(h[0]) if h else 0
    minutes = int(m[0]) if m else 0
    seconds = int(s[0]) if s else 0

    if not (h or m or s):
        try:
            minutes = int(time_str)
        except:
            return 0

    return hours * 3600 + minutes * 60 + seconds

# =========================
# EMBED BUILDERS
# =========================
def format_fruits(fruits) -> str:
    lines = []
    for rarity in RARITY_ORDER:
        for f in fruits:
            if FRUIT_DATA[f]["rarity"] != rarity:
                continue
            price_str = format_price(FRUIT_DATA[f]["price"])
            lines.append(
                f"{FRUIT_DATA[f]['emoji']} **{f.capitalize()}** "
                f"{RARITY_EMOJI[rarity]} `{rarity}` · {price_str}"
            )
    return "\n".join(lines)

def format_remaining(sec: int) -> str:
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

def build_embed(fruits, remaining: int, guild: discord.Guild = None) -> discord.Embed:
    timer_emoji = get_timer_emoji(guild)
    color       = get_embed_color(fruits) if fruits else 0x2B2D31

    embed = discord.Embed(title="🍇 Current Fruit Stock", color=color)
    embed.description = format_fruits(fruits) if fruits else "```\nNo fruits in stock.\n```"
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
    embed.set_footer(text="Auto-updates every 5s • King Legacy Stock")
    return embed

# =========================
# VIEW
# =========================
class StockView(View):
    def __init__(self):
        super().__init__(timeout=None)

# =========================
# COG
# =========================
class Stock(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_timer.start()

    # ── Permission check ──────────────────────────────────
    def is_permitted(self, ctx_or_interaction) -> bool:
        if isinstance(ctx_or_interaction, discord.Interaction):
            user     = ctx_or_interaction.user
            guild_id = ctx_or_interaction.guild_id
        else:
            user     = ctx_or_interaction.author
            guild_id = ctx_or_interaction.guild.id
        return user.guild_permissions.administrator or has_stock_perm(guild_id, user.id)

    # =========================
    # /perm
    # =========================
    @discord.app_commands.command(
        name="perm",
        description="Grant or revoke stock management permission for a user. (Admin only)"
    )
    @discord.app_commands.describe(
        action="Choose grant or revoke",
        user="The target user"
    )
    @discord.app_commands.choices(action=[
        discord.app_commands.Choice(name="grant",  value="grant"),
        discord.app_commands.Choice(name="revoke", value="revoke"),
    ])
    @discord.app_commands.default_permissions(administrator=True)
    @discord.app_commands.guild_only()
    async def perm(
        self,
        interaction: discord.Interaction,
        action: discord.app_commands.Choice[str],
        user: discord.Member,
    ):
        guild_id = interaction.guild_id
        perms    = load_perms(guild_id)
        val      = action.value

        if val == "grant":
            if user.id in perms["allowed_users"]:
                return await interaction.response.send_message(
                    f"⚠️ {user.mention} already has stock permission.", ephemeral=True
                )
            perms["allowed_users"].append(user.id)
            save_perms(guild_id, perms)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Permission Granted",
                    description=f"{user.mention} can now manage stock.",
                    color=0x2ECC71,
                ),
                ephemeral=True,
            )

        elif val == "revoke":
            if user.id not in perms["allowed_users"]:
                return await interaction.response.send_message(
                    f"⚠️ {user.mention} doesn't have stock permission.", ephemeral=True
                )
            perms["allowed_users"].remove(user.id)
            save_perms(guild_id, perms)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🚫 Permission Revoked",
                    description=f"{user.mention} can no longer manage stock.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

    # =========================
    # !addstock
    # =========================
    @commands.command()
    @commands.guild_only()
    async def addstock(self, ctx, *, fruits: str):
        if not self.is_permitted(ctx):
            return await ctx.send(
                embed=discord.Embed(
                    title="🚫 No Permission",
                    description="You don't have permission to manage stock.",
                    color=0xE74C3C,
                ),
                delete_after=5,
            )

        guild_id = ctx.guild.id
        data     = load_data(guild_id)
        inputs   = [f.strip() for f in fruits.split(",")]
        valid    = [match_fruit(f) for f in inputs if match_fruit(f)]
        invalid  = [f for f in inputs if not match_fruit(f)]

        if not valid:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Invalid Fruits",
                    description="None of the fruits entered are valid.",
                    color=0xE74C3C,
                ),
                delete_after=5,
            )

        prompt = discord.Embed(
            title="⏳ Set Timer",
            description="How long until stock resets?\n\nExample: `1h 30m` · `90m` · `3600s`",
            color=0x5865F2,
        )
        if invalid:
            prompt.set_footer(text=f"Ignored: {', '.join(invalid)}")
        await ctx.send(embed=prompt)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send("⏰ Timed out. Run `!addstock` again.", delete_after=5)

        seconds = parse_time(msg.content)
        if seconds <= 0:
            return await ctx.send("❌ Invalid time format.", delete_after=5)

        # Delete old stock message
        if data.get("channel_id") and data.get("message_id"):
            try:
                old_ch  = self.bot.get_channel(data["channel_id"])
                old_msg = await old_ch.fetch_message(data["message_id"])
                await old_msg.delete()
            except:
                pass

        data["fruits"]     = valid
        data["channel_id"] = ctx.channel.id
        data["reset_time"] = int(time.time()) + seconds
        data["notified"]   = False

        sent = await ctx.send(
            embed=build_embed(valid, seconds, ctx.guild),
            view=StockView(),
        )
        data["message_id"] = sent.id
        save_data(guild_id, data)

    # =========================
    # !stock
    # =========================
    @commands.command()
    @commands.guild_only()
    async def stock(self, ctx):
        guild_id  = ctx.guild.id
        data      = load_data(guild_id)
        remaining = data["reset_time"] - int(time.time())

        if not data["fruits"] or remaining <= 0:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ No Active Stock",
                    description="There is currently no active stock.",
                    color=0x2B2D31,
                ),
                delete_after=8,
            )

        sent = await ctx.send(
            embed=build_embed(data["fruits"], remaining, ctx.guild),
            view=StockView(),
        )
        data["channel_id"] = ctx.channel.id
        data["message_id"] = sent.id
        save_data(guild_id, data)

    # =========================
    # !howstock
    # =========================
    @commands.command()
    @commands.guild_only()
    async def howstock(self, ctx):
        embed = discord.Embed(title="📘 How to Use Stock Bot", color=0x5865F2)
        embed.add_field(name="1️⃣ Add Stock",  value="`!addstock dragon, dough, flame`", inline=False)
        embed.add_field(name="2️⃣ Set Timer",  value="`1h 30m` · `90m` · `3600s`",      inline=False)
        embed.add_field(name="3️⃣ View Stock", value="`!stock`",                         inline=False)
        embed.add_field(
            name="⚙️ System",
            value="• Auto countdown (updates every 5s)\n• 1 min warning\n• Auto reset on expire",
            inline=False,
        )
        embed.add_field(
            name="🔐 Permissions",
            value="Admins grant access with `/perm grant @user`",
            inline=False,
        )
        embed.set_footer(text="Separate fruits with commas!")
        await ctx.send(embed=embed)

    # =========================
    # AUTO-UPDATE LOOP
    # =========================
    @tasks.loop(seconds=5)
    async def check_timer(self):
        for guild in self.bot.guilds:
            guild_id  = guild.id
            data      = load_data(guild_id)

            if not data.get("channel_id") or not data.get("message_id"):
                continue

            remaining = data["reset_time"] - int(time.time())
            channel   = self.bot.get_channel(data["channel_id"])
            if not channel:
                continue

            # Edit live countdown
            if data["fruits"] and remaining > 0:
                try:
                    msg = await channel.fetch_message(data["message_id"])
                    await msg.edit(embed=build_embed(data["fruits"], remaining, guild))
                except:
                    pass

            # 1-min warning
            if remaining <= 60 and remaining > 0 and not data["notified"]:
                await channel.send("⚠️ Stock resets in **1 minute!**")
                data["notified"] = True
                save_data(guild_id, data)

            # Expired
            if remaining <= 0 and data["fruits"]:
                try:
                    msg = await channel.fetch_message(data["message_id"])
                    await msg.edit(
                        embed=discord.Embed(
                            title="🔄 Stock Expired",
                            description="Stock has been reset. Waiting for new stock...",
                            color=0x2B2D31,
                        ).set_footer(text="King Legacy Stock"),
                        view=None,
                    )
                except:
                    pass

                data["fruits"]     = []
                data["reset_time"] = 0
                data["notified"]   = False
                data["message_id"] = None
                save_data(guild_id, data)
                await channel.send("🔄 **Stock has been reset!**")

    @check_timer.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


# =========================
# SETUP
# =========================
async def setup(bot: commands.Bot):
    cog = Stock(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.perm)
