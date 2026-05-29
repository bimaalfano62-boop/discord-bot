import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
import os
import re

CONFIG_FILE = "config.json"

TOXIC_WORDS = [
    "fuck", "shit", "bitch", "asshole", "bastard", "damn", "crap",
    "pussy", "dick", "cock", "ass", "idiot", "stupid", "moron",
    "retard", "dumbass", "jackass", "prick", "slut", "whore",
    "faggot", "nigga", "nigger", "cunt", "motherfucker", "fucker",
    "nga", "bullshit", "goon", "gooner", "retard", "tard",
    "bajingan", "goblok", "tolol", "bodoh", "kampret", "sialan",
    "keparat", "tai", "jancok", "cok", "asu", "celeng", "babi",
]

PUNISH_MESSAGE = "punish me harder Daddy 🥺"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_allowed(interaction: discord.Interaction) -> bool:
    config = load_config()
    guild_id = str(interaction.guild.id)
    if interaction.user.id == interaction.guild.owner_id:
        return True
    allowed = config.get(guild_id, {}).get("allowed_users", [])
    return interaction.user.id in allowed

def contains_toxic(text: str) -> list:
    found = []
    text_lower = text.lower()
    for word in TOXIC_WORDS:
        if word in text_lower:
            found.append(word)
    return found

def censor_text(text: str, toxic_found: list) -> str:
    result = text
    for word in toxic_found:
        censored = word[0] + "*" * (len(word) - 2) + word[-1] if len(word) > 2 else "**"
        result = re.sub(re.escape(word), censored, result, flags=re.IGNORECASE)
    return result

async def get_or_create_punish_role(guild: discord.Guild) -> discord.Role:
    role = discord.utils.get(guild.roles, name="Punished 🔒")
    if not role:
        role = await guild.create_role(
            name="Punished 🔒",
            color=discord.Color.dark_gray(),
            reason="Auto-created by Troll bot"
        )
    return role

async def apply_punish_role(guild: discord.Guild, user_id: int):
    try:
        member = guild.get_member(user_id)
        if member:
            role = await get_or_create_punish_role(guild)
            await member.add_roles(role, reason="Punished by Troll bot")
    except Exception as e:
        print(f"Apply role error: {e}")

async def remove_punish_role(guild: discord.Guild, user_id: int):
    try:
        member = guild.get_member(user_id)
        if member:
            role = discord.utils.get(guild.roles, name="Punished 🔒")
            if role and role in member.roles:
                await member.remove_roles(role, reason="Unpunished by Troll bot")
    except Exception as e:
        print(f"Remove role error: {e}")

# =========================
# SETUP UI
# =========================
class MonitorSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select Monitor Channel",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.monitor_channel = self.values[0].id
        await interaction.response.send_message(
            f"✅ Monitor: <#{self.view.monitor_channel}>", ephemeral=True
        )

class DashboardSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select Dashboard Channel",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.dashboard_channel = self.values[0].id
        await interaction.response.send_message(
            f"✅ Dashboard: <#{self.view.dashboard_channel}>", ephemeral=True
        )

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.monitor_channel = None
        self.dashboard_channel = None
        self.add_item(MonitorSelect())
        self.add_item(DashboardSelect())

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.monitor_channel or not self.dashboard_channel:
            await interaction.response.send_message(
                "❌ Please select all channels first!", ephemeral=True
            )
            return
        config = load_config()
        guild_id = str(interaction.guild.id)
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["monitor"]   = self.monitor_channel
        config[guild_id]["dashboard"] = self.dashboard_channel
        config[guild_id].setdefault("allowed_users", [])
        config[guild_id].setdefault("punished_users", [])
        save_config(config)
        await interaction.response.send_message("✅ Setup saved!", ephemeral=True)

# =========================
# MODALS
# =========================
class ReplyModal(discord.ui.Modal, title="Reply Message"):
    reply = discord.ui.TextInput(label="Your reply", style=discord.TextStyle.paragraph)

    def __init__(self, message_id, channel_id):
        super().__init__()
        self.message_id = message_id
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(self.channel_id)
        try:
            msg = await channel.fetch_message(self.message_id)
            sent = await msg.reply(self.reply.value, mention_author=False)
            await interaction.response.send_message(
                "✅ Reply sent! (auto-deletes in 10s)", ephemeral=True
            )
            await sent.delete(delay=10)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

class SendMessageModal(discord.ui.Modal, title="Send Message"):
    message = discord.ui.TextInput(
        label="Message",
        placeholder="Type your message here...",
        style=discord.TextStyle.paragraph
    )

    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
            return
        try:
            sent = await channel.send(
                self.message.value,
                allowed_mentions=discord.AllowedMentions.none()
            )
            await interaction.response.send_message(
                "✅ Message sent! (auto-deletes in 10s)", ephemeral=True
            )
            await sent.delete(delay=10)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

class SendMediaModal(discord.ui.Modal, title="Send GIF / Image"):
    url = discord.ui.TextInput(
        label="GIF or Image URL",
        placeholder="https://tenor.com/... or https://i.imgur.com/...",
        style=discord.TextStyle.short
    )
    caption = discord.ui.TextInput(
        label="Caption (optional)",
        placeholder="Add a message...",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
            return

        valid_extensions = (".gif", ".png", ".jpg", ".jpeg", ".webp")
        valid_hosts = (
            "tenor.com", "giphy.com", "imgur.com", "i.imgur.com",
            "media.discordapp.net", "cdn.discordapp.com"
        )
        url_lower = self.url.value.lower()
        is_valid = (
            any(url_lower.endswith(ext) for ext in valid_extensions) or
            any(host in url_lower for host in valid_hosts)
        )

        if not is_valid:
            await interaction.response.send_message(
                "❌ Invalid URL. Use a direct image/GIF link from Tenor, Giphy, or Imgur.",
                ephemeral=True
            )
            return

        try:
            embed = discord.Embed(color=0x00ffff)
            embed.set_image(url=self.url.value)
            if self.caption.value:
                embed.description = self.caption.value
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            await interaction.response.send_message("✅ Sent!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

# =========================
# REPLY VIEW
# =========================
class ReplyView(discord.ui.View):
    def __init__(self, message_id, channel_id):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.channel_id = channel_id

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.blurple, emoji="💬")
    async def reply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return
        await interaction.response.send_modal(ReplyModal(self.message_id, self.channel_id))

    @discord.ui.button(label="Send Message", style=discord.ButtonStyle.grey, emoji="📨")
    async def send_message_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return
        await interaction.response.send_modal(SendMessageModal(self.channel_id))

    @discord.ui.button(label="Send GIF / Pic", style=discord.ButtonStyle.green, emoji="🖼️")
    async def send_media_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return
        await interaction.response.send_modal(SendMediaModal(self.channel_id))

# =========================
# TOXIC WARNING VIEW
# =========================
class ToxicWarningView(discord.ui.View):
    def __init__(self, user_id: int, guild_id: str):
        super().__init__(timeout=60)
        self.user_id  = user_id
        self.guild_id = guild_id

    @discord.ui.button(label="Punish", style=discord.ButtonStyle.danger, emoji="👊")
    async def punish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return

        config = load_config()
        if self.guild_id not in config:
            config[self.guild_id] = {}

        punished = config[self.guild_id].get("punished_users", [])
        if self.user_id in punished:
            await interaction.response.send_message(
                "⚠️ User is already being punished!", ephemeral=True
            )
            return

        punished.append(self.user_id)
        config[self.guild_id]["punished_users"] = punished
        save_config(config)

        await apply_punish_role(interaction.guild, self.user_id)

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        embed = discord.Embed(
            title="👊 User Punished!",
            description=(
                f"<@{self.user_id}> has been punished for toxic behavior!\n"
                f"Every message will now say **\"{PUNISH_MESSAGE}\"** 😈"
            ),
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Ignore", style=discord.ButtonStyle.secondary, emoji="🙈")
    async def ignore_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ Ignored.", ephemeral=True)

# =========================
# PERMISSION UI
# =========================
class AddUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Search and select users to allow...",
            min_values=1,
            max_values=10
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        if guild_id not in config:
            await interaction.response.send_message("❌ Run `/setup` first.", ephemeral=True)
            return

        allowed = config[guild_id].get("allowed_users", [])
        added, skipped = [], []

        for user in self.values:
            if user.bot:
                skipped.append(f"{user.name} (bot)")
            elif user.id in allowed:
                skipped.append(f"{user.name} (already allowed)")
            else:
                allowed.append(user.id)
                added.append(user.name)

        config[guild_id]["allowed_users"] = allowed
        save_config(config)

        msg = ""
        if added:   msg += f"✅ Added: `{'`, `'.join(added)}`\n"
        if skipped: msg += f"⚠️ Skipped: `{'`, `'.join(skipped)}`"
        await interaction.response.send_message(msg or "Nothing changed.", ephemeral=True)

class RemoveUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Search and select users to remove...",
            min_values=1,
            max_values=10
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        if guild_id not in config:
            await interaction.response.send_message("❌ Run `/setup` first.", ephemeral=True)
            return

        allowed = config[guild_id].get("allowed_users", [])
        removed, skipped = [], []

        for user in self.values:
            if user.id in allowed:
                allowed.remove(user.id)
                removed.append(user.name)
            else:
                skipped.append(user.name)

        config[guild_id]["allowed_users"] = allowed
        save_config(config)

        msg = ""
        if removed: msg += f"✅ Removed: `{'`, `'.join(removed)}`\n"
        if skipped: msg += f"⚠️ Not in list: `{'`, `'.join(skipped)}`"
        await interaction.response.send_message(msg or "Nothing changed.", ephemeral=True)

class PermissionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(AddUserSelect())
        self.add_item(RemoveUserSelect())

# =========================
# COG
# =========================
class Troll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Setup monitor & dashboard channel")
    async def setup(self, interaction: discord.Interaction):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return
        await interaction.response.send_message(
            "⚙️ Select channels:", view=SetupView(), ephemeral=True
        )

    @app_commands.command(name="resetsetup", description="Reset config & clear all messages")
    async def resetsetup(self, interaction: discord.Interaction):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild.id)

        if guild_id not in config:
            await interaction.response.send_message(
                "❌ No config found. Run `/setup` first.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        errors = []
        for key in ["monitor", "dashboard"]:
            ch_id = config[guild_id].get(key)
            if ch_id:
                try:
                    ch = interaction.guild.get_channel(ch_id)
                    if ch:
                        await ch.purge(limit=None)
                except Exception as e:
                    errors.append(f"{key.capitalize()}: {e}")

        del config[guild_id]
        save_config(config)

        if errors:
            await interaction.followup.send(
                "⚠️ Config reset but some errors:\n" + "\n".join(errors), ephemeral=True
            )
        else:
            await interaction.followup.send(
                "✅ All messages cleared and config deleted. Run `/setup` to reconfigure.",
                ephemeral=True
            )

    @app_commands.command(name="permissions", description="Manage who can access Troll features")
    async def permissions(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ Only the server owner can manage permissions.", ephemeral=True
            )
            return

        config = load_config()
        guild_id = str(interaction.guild.id)
        allowed = config.get(guild_id, {}).get("allowed_users", [])

        desc = (
            ("**Currently allowed users:**\n" + "\n".join([f"<@{uid}>" for uid in allowed]) + "\n\n")
            if allowed else "**No users allowed yet.**\n\n"
        )
        desc += "Use the dropdowns below to add or remove users."

        embed = discord.Embed(
            title="🔐 Troll Feature Permissions",
            description=desc,
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, view=PermissionView(), ephemeral=True)

    @app_commands.command(name="punish", description="Punish me daddy!?")
    @app_commands.describe(user="Select user to punish")
    async def punish(self, interaction: discord.Interaction, user: discord.Member):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return
        if user.bot:
            await interaction.response.send_message("❌ Can't punish a bot.", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild.id)
        if guild_id not in config:
            config[guild_id] = {}

        punished = config[guild_id].get("punished_users", [])
        if user.id in punished:
            await interaction.response.send_message(
                f"⚠️ {user.mention} is already being punished!", ephemeral=True
            )
            return

        punished.append(user.id)
        config[guild_id]["punished_users"] = punished
        save_config(config)

        await apply_punish_role(interaction.guild, user.id)

        embed = discord.Embed(
            title="👊 User Punished!",
            description=(
                f"{user.mention} has been punished!\n"
                f"Every message will now say **\"{PUNISH_MESSAGE}\"** 😈"
            ),
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)

@app_commands.command(name="unpunish", description="Remove punishment from a user")
    @app_commands.describe(user="Select user to unpunish")
    async def unpunish(self, interaction: discord.Interaction, user: discord.Member):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild.id)
        punished = config.get(guild_id, {}).get("punished_users", [])

        if user.id not in punished:
            await interaction.response.send_message(
                f"⚠️ {user.mention} is not being punished.", ephemeral=True
            )
            return

        punished.remove(user.id)
        config[guild_id]["punished_users"] = punished
        save_config(config)

        await remove_punish_role(interaction.guild, user.id)

        embed = discord.Embed(
            title="✅ Punishment Removed",
            description=f"{user.mention} has been freed from punishment.",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="punishlist", description="See all currently punished users")
    async def punishlist(self, interaction: discord.Interaction):
        if not is_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild.id)
        punished = config.get(guild_id, {}).get("punished_users", [])

        if not punished:
            await interaction.response.send_message(
                "✅ No users are currently being punished.", ephemeral=True
            )
            return

        mentions = "\n".join([f"• <@{uid}>" for uid in punished])
        embed = discord.Embed(title="😈 Punished Users", description=mentions, color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return

        config = load_config()
        guild_id = str(message.guild.id)

        if guild_id not in config:
            return

        # PUNISH LOGIC
        punished = config[guild_id].get("punished_users", [])
        if message.author.id in punished and message.content:
            try:
                await message.delete()
                await message.channel.send(
                    f"**{message.author.display_name}:** {PUNISH_MESSAGE}",
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except Exception as e:
                print(f"Punish error: {e}")
            return

        # TOXIC DETECTION
        if message.content:
            toxic_found = contains_toxic(message.content)
            if toxic_found:
                dashboard_id = config[guild_id].get("dashboard")
                if dashboard_id:
                    dashboard = self.bot.get_channel(dashboard_id)
                    if dashboard:
                        censored = censor_text(message.content, toxic_found)
                        embed = discord.Embed(
                            title="⚠️ Toxic Message Detected!",
                            color=0xFF4500
                        )
                        embed.add_field(name="👤 User",        value=message.author.mention,                    inline=False)
                        embed.add_field(name="💬 Message",     value=censored,                                   inline=False)
                        embed.add_field(name="🤬 Toxic Words", value=", ".join([f"`{w}`" for w in toxic_found]), inline=False)
                        embed.add_field(name="📍 Channel",     value=message.channel.mention,                    inline=False)
                        embed.add_field(name="⏰ Time",        value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
                        embed.set_thumbnail(url=message.author.display_avatar.url)
                        embed.set_footer(text=f"User ID: {message.author.id}")
                        await dashboard.send(
                            embed=embed,
                            view=ToxicWarningView(message.author.id, guild_id)
                        )

        # MONITOR LOGIC
        monitor_id   = config[guild_id].get("monitor")
        dashboard_id = config[guild_id].get("dashboard")

        if not monitor_id or not dashboard_id:
            return
        if message.channel.id != monitor_id:
            return

        dashboard = self.bot.get_channel(dashboard_id)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        embed = discord.Embed(
            title="📩 Incoming Message",
            color=0x00ffff,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="👤 User",    value=message.author.mention,  inline=False)
        embed.add_field(name="💬 Message", value=message.content or "-",  inline=False)
        embed.add_field(name="📍 Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="⏰ Time",    value=now,                     inline=False)
        embed.set_footer(text=f"Message ID: {message.id}")

        await dashboard.send(embed=embed, view=ReplyView(message.id, message.channel.id))


async def setup(bot):
    await bot.add_cog(Troll(bot))

