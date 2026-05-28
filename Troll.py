import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect
import json
import time
import os

# =========================
# TOKEN (ENV)
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN belum di set!")

DATA_FILE = "data.json"
CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# UTIL
# =========================
def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

data_db = load_json(DATA_FILE, {})
config = load_json(CONFIG_FILE, {})

# =========================
# SETUP UI (TIDAK BERUBAH)
# =========================
class SetupView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.monitor = None
        self.dashboard = None

        self.add_item(ChannelPicker("Pilih Channel Monitor", "monitor"))
        self.add_item(ChannelPicker("Pilih Channel Dashboard", "dashboard"))

class ChannelPicker(ChannelSelect):
    def __init__(self, placeholder, mode):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.mode = mode

    async def callback(self, interaction):
        channel = self.values[0]
        view = self.view

        if self.mode == "monitor":
            view.monitor = channel.id
        else:
            view.dashboard = channel.id

        await interaction.response.send_message(
            f"✅ {self.mode} set ke {channel.mention}",
            ephemeral=True
        )

class SaveButton(Button):
    def __init__(self):
        super().__init__(label="Save", style=discord.ButtonStyle.green)

    async def callback(self, interaction):
        view = self.view

        if not view.monitor or not view.dashboard:
            await interaction.response.send_message(
                "❌ Pilih semua channel dulu", ephemeral=True
            )
            return

        config[str(interaction.guild.id)] = {
            "monitor": view.monitor,
            "dashboard": view.dashboard
        }

        save_json(CONFIG_FILE, config)

        await interaction.response.send_message(
            "✅ Setup berhasil!", ephemeral=True
        )

# =========================
# REPLY SYSTEM
# =========================
class ReplyModal(Modal, title="Balas Pesan"):
    def __init__(self, message_id, channel_id):
        super().__init__()
        self.message_id = message_id
        self.channel_id = channel_id

        self.reply_text = TextInput(label="Balasan", style=discord.TextStyle.long)
        self.add_item(self.reply_text)

    async def on_submit(self, interaction):
        channel = interaction.client.get_channel(self.channel_id)
        msg = await channel.fetch_message(self.message_id)

        await msg.reply(self.reply_text.value)

        await interaction.response.send_message("✅ Terkirim", ephemeral=True)

class ReplyButton(Button):
    def __init__(self, message_id, channel_id):
        super().__init__(label="Reply", style=discord.ButtonStyle.primary)
        self.message_id = message_id
        self.channel_id = channel_id

    async def callback(self, interaction):
        await interaction.response.send_modal(
            ReplyModal(self.message_id, self.channel_id)
        )

class ReplyView(View):
    def __init__(self, message_id, channel_id):
        super().__init__(timeout=None)
        self.add_item(ReplyButton(message_id, channel_id))

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"Login sebagai {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash command sync: {len(synced)}")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.guild:
        return

    guild_id = str(message.guild.id)
    if guild_id not in config:
        return

    monitor_id = config[guild_id]["monitor"]
    dashboard_id = config[guild_id]["dashboard"]

    if message.channel.id != monitor_id:
        return

    # SAVE DATA
    data_db[str(message.id)] = {
        "user": str(message.author),
        "user_id": message.author.id,
        "content": message.content,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "channel_id": message.channel.id
    }

    save_json(DATA_FILE, data_db)

    # SEND TO DASHBOARD
    dashboard = bot.get_channel(dashboard_id)
    if not dashboard:
        return

    view = ReplyView(message.id, message.channel.id)

    await dashboard.send(
        f"📩 **Pesan Baru**\n"
        f"👤 {message.author}\n"
        f"💬 {message.content}\n"
        f"⏰ {data_db[str(message.id)]['time']}",
        view=view
    )

    await bot.process_commands(message)

# =========================
# COMMANDS
# =========================
@bot.tree.command(name="setup", description="Setup bot")
async def setup(interaction: discord.Interaction):
    view = SetupView()
    view.add_item(SaveButton())

    await interaction.response.send_message(
        "⚙️ Pilih channel:", view=view, ephemeral=True
    )

@bot.tree.command(name="history", description="Lihat history user")
@app_commands.describe(user="User target")
async def history(interaction: discord.Interaction, user: discord.User):
    results = [
        v for v in data_db.values()
        if v["user_id"] == user.id
    ][-5:]

    if not results:
        await interaction.response.send_message("❌ Tidak ada data", ephemeral=True)
        return

    text = ""
    for d in results:
        text += f"💬 {d['content']} ({d['time']})\n"

    await interaction.response.send_message(text, ephemeral=True)

# =========================
bot.run(TOKEN)
