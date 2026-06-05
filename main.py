import discord
import json
import os
import time
import asyncio
import random
from datetime import datetime
from discord.ext import commands
from groq import AsyncGroq
from dotenv import load_dotenv

# ============================================
#           LOAD ENVIRONMENT & CONFIG
# ============================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

config = load_config()

# ============================================
#         SETUP AI & SELFBOT
# ============================================
if not DISCORD_TOKEN:
    print("❌ Discord Token not found in .env file!")
    exit()

ai_client = AsyncGroq(api_key=GROQ_KEY) if GROQ_KEY else None

class SelfBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=config["prefix"],
            self_bot=True,
            help_command=None,
        )
        self.afk = config["afk"]
        self.auto_reply = config["auto_reply"]
        self.anti_delete = config["anti_delete"]
        self.ai_cfg = config.get("ai", {})
        self.sniped_messages = {}
        self.edited_messages = {}
        self.start_time = None

    async def on_ready(self):
        self.start_time = datetime.now()
        print(f"""
╔══════════════════════════════════╗
║     ALL-IN-ONE SELFBOT READY    ║
╠══════════════════════════════════╣
║  User  : {self.user.name:<22}║
║  ID    : {self.user.id:<22}║
║  Prefix: {config['prefix']:<22}║
║  AI    : {'✅ Groq Active' if self.ai_cfg.get('enabled') and ai_client else '❌ Off':<22}║
╚══════════════════════════════════╝
        """)
        status_cfg = config.get("status", {})
        if status_cfg.get("text"):
            status_type = status_cfg.get("type", "listening")
            if status_type == "listening":
                act = discord.Activity(type=discord.ActivityType.listening, name=status_cfg["text"])
            elif status_type == "playing":
                act = discord.Game(name=status_cfg["text"])
            elif status_type == "watching":
                act = discord.Activity(type=discord.ActivityType.watching, name=status_cfg["text"])
            else:
                act = discord.Game(name=status_cfg["text"])
            await self.change_presence(activity=act)

bot = SelfBot()

# ============================================
#           UTILITY & AI FUNCTIONS
# ============================================
def get_uptime():
    if not bot.start_time: return "N/A"
    delta = datetime.now() - bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def embed_builder(title, description, color=0x00ff00):
    em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
    em.set_footer(text=f"Selfbot | {bot.user}", icon_url=bot.user.avatar.url if bot.user.avatar else "")
    return em

async def generate_ai_response(prompt):
    if not ai_client:
        return "❌ Groq API Key is not set in the `.env` file."
    try:
        response = await ai_client.chat.completions.create(
            model=bot.ai_cfg.get("model", "llama3-8b-8192"),
            messages=[
                {"role": "system", "content": bot.ai_cfg.get("system_prompt", "You are a helpful assistant.")},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Groq AI Error: `{e}`"

# ============================================
#           MASTER EVENT on_message
# ============================================
@bot.event
async def on_message(message):
    # If message is from the bot owner (you)
    if message.author.id == bot.user.id:
        if bot.afk["enabled"]:
            bot.afk["enabled"] = False
            config["afk"]["enabled"] = False
            save_config(config)
        await bot.process_commands(message)
        return

    mentioned = bot.user.mentioned_in(message)

    # PRIORITY 1: AFK
    if mentioned and bot.afk["enabled"]:
        try: await message.reply(f"💤 I'm currently AFK: {bot.afk['message']}")
        except: pass

    # PRIORITY 2: AI Reply (Groq)
    elif mentioned and bot.ai_cfg.get("enabled", False) and bot.ai_cfg.get("reply_on_mention", True):
        content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if content:
            async with message.channel.typing():
                reply = await generate_ai_response(content)
                if len(reply) > 2000: reply = reply[:1997] + "..."
                try: await message.reply(reply)
                except: pass

    # PRIORITY 3: Auto Reply Triggers
    if bot.auto_reply["enabled"] and not mentioned:
        content_lower = message.content.lower().strip()
        for trigger, reply in bot.auto_reply.get("triggers", {}).items():
            if trigger.lower() in content_lower:
                try: await message.reply(reply)
                except: pass
                break

    # Save for Snipe
    bot.sniped_messages[message.channel.id] = {
        "content": message.content, "author": message.author,
        "time": datetime.now(), "attachments": message.attachments
    }

@bot.event
async def on_message_edit(before, after):
    if before.author.id == bot.user.id: return
    bot.edited_messages[before.channel.id] = {
        "before": before.content, "after": after.content,
        "author": before.author, "time": datetime.now()
    }

@bot.event
async def on_message_delete(message):
    if message.author.id == bot.user.id: return
    
    # Anti Delete Log
    if bot.anti_delete["enabled"] and bot.anti_delete.get("channel_id"):
        log_channel = bot.get_channel(int(bot.anti_delete["channel_id"]))
        if log_channel:
            em = discord.Embed(title="🗑️ Message Deleted", color=0xff0000, timestamp=datetime.now())
            em.add_field(name="Author", value=f"{message.author} (`{message.author.id}`)", inline=False)
            em.add_field(name="Channel", value=f"{message.channel.mention}", inline=True)
            content = message.content or "*No text content*"
            if len(content) > 1024: content = content[:1021] + "..."
            em.add_field(name="Content", value=content, inline=False)
            try: await log_channel.send(embed=em)
            except: pass

    # Snipe
    bot.sniped_messages[message.channel.id] = {
        "content": message.content, "author": message.author,
        "time": datetime.now(), "attachments": message.attachments
    }

# ============================================
#           COMMANDS - HELP
# ============================================
@bot.command(name="help")
async def help_cmd(ctx):
    em = embed_builder("📖 Selfbot Commands", f"Prefix: `{config['prefix']}`")
    categories = {
        "🤖 AI (Groq)": [
            f"`{config['prefix']}ask <question>` - Ask AI manually",
            f"`{config['prefix']}aitoggle <on/off>` - Toggle AI auto-reply",
            f"`{config['prefix']}aiprompt <text>` - Change AI personality",
            f"`{config['prefix']}aimodel <model>` - Change model (llama3/mixtral)",
            f"`{config['prefix']}aiconfig` - View current AI settings",
        ],
        "🛠️ Utility": [
            f"`{config['prefix']}ping` - Check latency",
            f"`{config['prefix']}uptime` - Check uptime",
            f"`{config['prefix']}userinfo [user]` - User info",
            f"`{config['prefix']}avatar [user]` - Get avatar",
            f"`{config['prefix']}calc <expr>` - Calculator",
        ],
        "💬 Message": [
            f"`{config['prefix']}purge <amount>` - Delete your own messages",
            f"`{config['prefix']}spam <amount> <text>` - Spam messages",
            f"`{config['prefix']}embed <text>` - Send embed message",
            f"`{config['prefix']}dm <user> <text>` - Send DM",
        ],
        "🔍 Snipe & Auto": [
            f"`{config['prefix']}snipe` - View deleted messages",
            f"`{config['prefix']}editsnipe` - View edited messages",
            f"`{config['prefix']}afk <on/off/msg>` - Toggle AFK",
            f"`{config['prefix']}autoreply <on/off>` - Toggle keyword reply",
            f"`{config['prefix']}addtrigger <t>|<r>` - Add trigger",
            f"`{config['prefix']}antidelete <on/off> [ch]` - Log deleted messages",
        ],
        "🎮 Fun": [
            f"`{config['prefix']}8ball <question>` - Magic 8ball",
            f"`{config['prefix']}roll [max]` - Roll dice",
            f"`{config['prefix']}coinflip` - Coin flip",
            f"`{config['prefix']}rps <choice>` - Rock paper scissors",
            f"`{config['prefix']}gayrate [user]` - Gay rate",
        ],
        "⚙️ Settings": [
            f"`{config['prefix']}setprefix <prefix>` - Change prefix",
            f"`{config['prefix']}setstatus <type> <text>` - Change status",
        ],
    }
    for cat, cmds in categories.items():
        em.add_field(name=cat, value="\n".join(cmds), inline=False)
    await ctx.send(embed=em)

# ============================================
#           COMMANDS - AI
# ============================================
@bot.command(name="ask")
async def ask_cmd(ctx, *, question):
    async with ctx.typing():
        reply = await generate_ai_response(question)
        if len(reply) > 2000: reply = reply[:1997] + "..."
        await ctx.send(reply)

@bot.command(name="aitoggle")
async def aitoggle_cmd(ctx, state="on"):
    if state.lower() == "off":
        bot.ai_cfg["enabled"] = False; config["ai"]["enabled"] = False
        save_config(config); await ctx.send("🔴 AI Auto-Reply **disabled**.")
    else:
        bot.ai_cfg["enabled"] = True; config["ai"]["enabled"] = True
        save_config(config); await ctx.send("🟢 AI Auto-Reply **enabled**.")

@bot.command(name="aiprompt")
async def aiprompt_cmd(ctx, *, new_prompt):
    bot.ai_cfg["system_prompt"] = new_prompt; config["ai"]["system_prompt"] = new_prompt
    save_config(config); await ctx.send(f"✅ System Prompt changed to:\n```{new_prompt}```")

@bot.command(name="aimodel")
async def aimodel_cmd(ctx, model="llama3-8b-8192"):
    bot.ai_cfg["model"] = model; config["ai"]["model"] = model
    save_config(config); await ctx.send(f"✅ AI Model changed to `{model}`")

@bot.command(name="aiconfig")
async def aiconfig_cmd(ctx):
    em = embed_builder("⚙️ AI Configuration (Groq)", 
        f"**Enabled:** {'✅' if bot.ai_cfg['enabled'] else '❌'}\n"
        f"**Model:** `{bot.ai_cfg['model']}`\n"
        f"**Reply on Mention:** {'✅' if bot.ai_cfg.get('reply_on_mention') else '❌'}\n"
        f"**System Prompt:** ```{bot.ai_cfg['system_prompt']}```")
    await ctx.send(embed=em)

# ============================================
#           COMMANDS - UTILITY
# ============================================
@bot.command(name="ping")
async def ping_cmd(ctx):
    start = time.perf_counter(); msg = await ctx.send("🏓 Pinging...")
    end = time.perf_counter(); latency = round((end - start) * 1000)
    em = embed_builder("🏓 Pong!", f"**Latency:** `{latency}ms`")
    await msg.edit(content=None, embed=em)

@bot.command(name="uptime")
async def uptime_cmd(ctx):
    em = embed_builder("⏰ Uptime", f"`{get_uptime()}`"); await ctx.send(embed=em)

@bot.command(name="userinfo", aliases=["ui"])
async def userinfo_cmd(ctx, user: discord.User = None):
    user = user or ctx.author; member = ctx.guild.get_member(user.id) if ctx.guild else None
    em = discord.Embed(title=f"👤 {user}", color=0x00ff00, timestamp=datetime.now())
    em.set_thumbnail(url=user.avatar.url if user.avatar else "")
    em.add_field(name="ID", value=user.id, inline=True)
    em.add_field(name="Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
    if member:
        em.add_field(name="Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        roles = [r.mention for r in member.roles[1:]] or ["None"]
        em.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles[:10]), inline=False)
    await ctx.send(embed=em)

@bot.command(name="avatar", aliases=["av"])
async def avatar_cmd(ctx, user: discord.User = None):
    user = user or ctx.author
    if not user.avatar: return await ctx.send("❌ User has no avatar!")
    em = embed_builder("🖼️ Avatar", f"[Download]({user.avatar.url})"); em.set_image(url=user.avatar.url)
    await ctx.send(embed=em)

@bot.command(name="calc")
async def calc_cmd(ctx, *, expression):
    try:
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression): return await ctx.send("❌ Invalid expression!")
        result = eval(expression)
        await ctx.send(embed=embed_builder("🧮 Calculator", f"**Input:** `{expression}`\n**Output:** `{result}`"))
    except Exception as e: await ctx.send(f"❌ Error: `{e}`")

# ============================================
#           COMMANDS - MESSAGE
# ============================================
@bot.command(name="purge", aliases=["clear"])
async def purge_cmd(ctx, amount: int = 10):
    if amount > 100: return await ctx.send("❌ Maximum 100 messages!")
    deleted = 0
    async for message in ctx.channel.history(limit=200):
        if message.author.id == bot.user.id:
            if deleted >= amount: break
            await message.delete(); deleted += 1; await asyncio.sleep(0.5)
    msg = await ctx.send(embed=embed_builder("🗑️ Purge", f"Successfully deleted `{deleted}` messages!"))
    await asyncio.sleep(3); await msg.delete()

@bot.command(name="spam")
async def spam_cmd(ctx, amount: int = 5, *, text):
    if amount > 20: return await ctx.send("❌ Maximum 20 messages!")
    for i in range(amount):
        try: await ctx.send(text); await asyncio.sleep(0.8)
        except discord.HTTPException: await asyncio.sleep(5)

@bot.command(name="embed")
async def embed_cmd(ctx, *, text):
    em = embed_builder("💬 Embed Message", text, color=random.randint(0, 0xffffff))
    await ctx.send(embed=em); await ctx.message.delete()

@bot.command(name="dm")
async def dm_cmd(ctx, user: discord.User, *, text):
    try: await user.send(text); await ctx.send(embed=embed_builder("📬 DM Sent", f"To: **{user}**\nMessage: `{text}`"))
    except discord.Forbidden: await ctx.send("❌ Cannot DM this user!")

# ============================================
#           COMMANDS - SNIPE & AUTO
# ============================================
@bot.command(name="snipe")
async def snipe_cmd(ctx):
    data = bot.sniped_messages.get(ctx.channel.id)
    if not data: return await ctx.send("❌ No messages to snipe!")
    em = discord.Embed(title="🔍 Sniped!", description=data["content"] or "*No text content*", color=0xff9900, timestamp=data["time"])
    em.set_footer(text=f"{data['author']} • ID: {data['author'].id}")
    if data["attachments"]: em.set_image(url=data["attachments"][0].url)
    await ctx.send(embed=em)

@bot.command(name="editsnipe", aliases=["esnipe"])
async def editsnipe_cmd(ctx):
    data = bot.edited_messages.get(ctx.channel.id)
    if not data: return await ctx.send("❌ No edited messages to snipe!")
    em = discord.Embed(title="✏️ Edit Sniped!", color=0xff9900, timestamp=data["time"])
    em.add_field(name="Before", value=data["before"] or "*Empty*", inline=False)
    em.add_field(name="After", value=data["after"] or "*Empty*", inline=False)
    em.set_footer(text=f"{data['author']} • ID: {data['author'].id}")
    await ctx.send(embed=em)

@bot.command(name="afk")
async def afk_cmd(ctx, *, action="on"):
    if action.lower() in ["off", "disable"]:
        bot.afk["enabled"] = False; config["afk"]["enabled"] = False; save_config(config)
        em = embed_builder("💤 AFK", "AFK **disabled**")
    elif action.lower() in ["on", "enable"]:
        bot.afk["enabled"] = True; bot.afk["message"] = "I'm currently AFK"
        config["afk"]["enabled"] = True; config["afk"]["message"] = "I'm currently AFK"; save_config(config)
        em = embed_builder("💤 AFK", "AFK **enabled**")
    else:
        bot.afk["enabled"] = True; bot.afk["message"] = action
        config["afk"]["enabled"] = True; config["afk"]["message"] = action; save_config(config)
        em = embed_builder("💤 AFK", f"AFK **enabled**\nMessage: `{action}`")
    await ctx.send(embed=em)

@bot.command(name="autoreply")
async def autoreply_cmd(ctx, action="on"):
    if action.lower() in ["off", "disable"]:
        bot.auto_reply["enabled"] = False; config["auto_reply"]["enabled"] = False; save_config(config)
        em = embed_builder("💬 Auto Reply", "Auto Reply **disabled**")
    else:
        bot.auto_reply["enabled"] = True; config["auto_reply"]["enabled"] = True; save_config(config)
        triggers = "\n".join([f"`{k}` → `{v}`" for k, v in bot.auto_reply.get("triggers", {}).items()]) or "Empty"
        em = embed_builder("💬 Auto Reply", f"Auto Reply **enabled**\n\n**Triggers:**\n{triggers}")
    await ctx.send(embed=em)

@bot.command(name="addtrigger")
async def addtrigger_cmd(ctx, *, text):
    parts = text.split("|")
    if len(parts) < 2: return await ctx.send("❌ Format: `addtrigger trigger|reply`")
    trigger, reply = parts[0].strip(), "|".join(parts[1:]).strip()
    bot.auto_reply.setdefault("triggers", {})[trigger] = reply; config["auto_reply"]["triggers"][trigger] = reply
    save_config(config); await ctx.send(embed=embed_builder("✅ Trigger Added", f"`{trigger}` → `{reply}`"))

@bot.command(name="antidelete")
async def antidelete_cmd(ctx, action="on", channel: discord.TextChannel = None):
    if action.lower() in ["off", "disable"]:
        bot.anti_delete["enabled"] = False; config["anti_delete"]["enabled"] = False; save_config(config)
        em = embed_builder("🛡️ Anti Delete", "Anti Delete **disabled**")
    else:
        ch = channel or ctx.channel; bot.anti_delete["enabled"] = True; bot.anti_delete["channel_id"] = str(ch.id)
        config["anti_delete"]["enabled"] = True; config["anti_delete"]["channel_id"] = str(ch.id); save_config(config)
        em = embed_builder("🛡️ Anti Delete", f"Anti Delete **enabled**\nLog Channel: {ch.mention}")
    await ctx.send(embed=em)

# ============================================
#           COMMANDS - FUN
# ============================================
@bot.command(name="8ball")
async def eightball_cmd(ctx, *, question):
    responses = ["🟢 Definitely!", "🟢 Without a doubt!", "🟡 Most likely", "🟡 Try asking again", "🔴 Don't count on it!", "🔴 No way!"]
    em = embed_builder("🎱 Magic 8-Ball", f"**Question:** {question}\n**Answer:** {random.choice(responses)}")
    await ctx.send(embed=em)

@bot.command(name="roll")
async def roll_cmd(ctx, max_num: int = 6):
    em = embed_builder("🎲 Dice Roll", f"Rolling 1-{max_num}...\n🎯 **{random.randint(1, max_num)}**")
    await ctx.send(embed=em)

@bot.command(name="coinflip", aliases=["cf"])
async def coinflip_cmd(ctx):
    await ctx.send(embed=embed_builder("Coin Flip", random.choice(["🪙 Heads!", "🪙 Tails!"])))

@bot.command(name="rps")
async def rps_cmd(ctx, choice):
    choice = choice.lower()
    if choice not in ["rock", "paper", "scissors", "r", "p", "s"]:
        return await ctx.send("❌ Choose: rock/paper/scissors")
    choices = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    norm = {"r": "rock", "p": "paper", "s": "scissors"}
    user_c = norm.get(choice, choice); bot_c = random.choice(list(choices.keys()))
    if user_c == bot_c: res = "🟡 Draw!"
    elif (user_c == "rock" and bot_c == "scissors") or (user_c == "paper" and bot_c == "rock") or (user_c == "scissors" and bot_c == "paper"): res = "🟢 You Win!"
    else: res = "🔴 You Lose!"
    em = embed_builder("✊ RPS", f"**You:** {choices[user_c]} {user_c.title()}\n**Bot:** {choices[bot_c]} {bot_c.title()}\n\n{res}")
    await ctx.send(embed=em)

@bot.command(name="gayrate")
async def gayrate_cmd(ctx, user: discord.User = None):
    user = user or ctx.author; rate = random.randint(0, 100)
    bar = "█" * int(rate/10) + "░" * (10 - int(rate/10))
    label = "Straight 😤" if rate < 30 else "Curious 💅" if rate < 60 else "Fabulous 🏳️‍🌈" if rate < 90 else "ULTRA GAY 🌈✨"
    await ctx.send(embed=embed_builder("🌈 Gay Rate", f"**{user}** is {rate}% gay!\n`[{bar}]` {label}"))

# ============================================
#           COMMANDS - SETTINGS
# ============================================
@bot.command(name="setprefix")
async def setprefix_cmd(ctx, new_prefix):
    config["prefix"] = new_prefix; bot.command_prefix = new_prefix; save_config(config)
    await ctx.send(embed=embed_builder("⚙️ Prefix Changed", f"New prefix: `{new_prefix}`"))

@bot.command(name="setstatus")
async def setstatus_cmd(ctx, status_type, *, text):
    status_type = status_type.lower()
    if status_type == "playing": act = discord.Game(name=text)
    elif status_type == "listening": act = discord.Activity(type=discord.ActivityType.listening, name=text)
    elif status_type == "watching": act = discord.Activity(type=discord.ActivityType.watching, name=text)
    elif status_type == "clear": await bot.change_presence(activity=None); return await ctx.send("🗑️ Status cleared!")
    else: return await ctx.send("❌ Types: playing/listening/watching/clear")
    await bot.change_presence(activity=act)
    config["status"] = {"type": status_type, "text": text}; save_config(config)
    await ctx.send(embed=embed_builder("⚙️ Status Changed", f"**Type:** {status_type}\n**Text:** {text}"))

# ============================================
#           ERROR HANDLER & RUN
# ============================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): return
    elif isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"❌ Missing argument! Check `{config['prefix']}help`")
    else: await ctx.send(f"❌ Error: `{error}`")

if __name__ == "__main__":
    print("Starting All-In-One Selfbot (Groq AI)...")
    try: bot.run(DISCORD_TOKEN, log_handler=None)
    except discord.LoginFailure: print("❌ Invalid Discord Token! Check your .env file.")
    except Exception as e: print(f"❌ Error: {e}")
