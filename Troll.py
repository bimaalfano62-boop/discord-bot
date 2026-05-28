import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
import os

TOKEN = "DISCORD_TOKEN"

CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG
# =========================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# SETUP UI
# =========================

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.monitor_channel = None
        self.dashboard_channel = None

    @discord.ui.channel_select(
        placeholder="Pilih Channel Monitor",
        channel_types=[discord.ChannelType.text]
    )
    async def monitor_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.monitor_channel = select.values[0].id
        await interaction.response.send_message(f"✅ Monitor: <#{self.monitor_channel}>", ephemeral=True)

    @discord.ui.channel_select(
        placeholder="Pilih Channel Dashboard",
        channel_types=[discord.ChannelType.text]
    )
    async def dashboard_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.dashboard_channel = select.values[0].id
        await interaction.response.send_message(f"✅ Dashboard: <#{self.dashboard_channel}>", ephemeral=True)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.monitor_channel or not self.dashboard_channel:
            await interaction.response.send_message("❌ Pilih semua dulu!", ephemeral=True)
            return

        config = load_config()
        config[str(interaction.guild.id)] = {
            "monitor": self.monitor_channel,
            "dashboard": self.dashboard_channel
        }
        save_config(config)

        await interaction.response.send_message("🔥 Setup berhasil!", ephemeral=True)

# =========================
# REPLY UI
# =========================

class ReplyModal(discord.ui.Modal, title="Balas Pesan"):
    reply = discord.ui.TextInput(label="Isi balasan", style=discord.TextStyle.paragraph)

    def __init__(self, message_id, channel_id):
        super().__init__()
        self.message_id = message_id
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = bot.get_channel(self.channel_id)
        try:
            msg = await channel.fetch_message(self.message_id)
            await msg.reply(self.reply.value)
            await interaction.response.send_message("✅ Terkirim!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Gagal kirim!", ephemeral=True)

class ReplyView(discord.ui.View):
    def __init__(self, message_id, channel_id):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.channel_id = channel_id

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.blurple)
    async def reply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReplyModal(self.message_id, self.channel_id))

# =========================
# COMMAND
# =========================

@bot.tree.command(name="setup", description="Setup bot")
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message(
        "⚙️ Pilih channel:",
        view=SetupView(),
        ephemeral=True
    )

# =========================
# MONITOR MESSAGE
# =========================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.guild:
        return

    config = load_config()
    guild_id = str(message.guild.id)

    if guild_id not in config:
        return

    monitor_id = config[guild_id]["monitor"]
    dashboard_id = config[guild_id]["dashboard"]

    if message.channel.id != monitor_id:
        return

    dashboard = bot.get_channel(dashboard_id)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(
        title="📩 Pesan Masuk",
        color=0x00ffff,
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name="👤 User", value=message.author.mention, inline=False)
    embed.add_field(name="💬 Pesan", value=message.content or "-", inline=False)
    embed.add_field(name="📍 Channel", value=message.channel.mention, inline=False)
    embed.add_field(name="⏰ Waktu", value=now, inline=False)

    embed.set_footer(text=f"Message ID: {message.id}")

    await dashboard.send(
        embed=embed,
        view=ReplyView(message.id, message.channel.id)
    )

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    print(f"Login sebagai {bot.user}")

    try:
        await bot.tree.sync()
        print("✅ Slash command global ready")
    except Exception as e:
        print(e)

bot.run(TOKEN)
