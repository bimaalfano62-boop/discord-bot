import discord
import json
import os
import time
import asyncio
import random
import sys
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
#         SETUP AI & BOT
# ============================================
if not DISCORD_TOKEN:
    print("❌ Bot Token not found in .env or Variables!")
    sys.exit(1)

ai_client = AsyncGroq(api_key=GROQ_KEY) if GROQ_KEY else None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class AIBot(commands.Bot):
    def __init__(self):
        default_prefix = config.get("prefix", "!")
        super().__init__(
            command_prefix=[default_prefix, ","],
            intents=intents,
            help_command=None
        )
        self.afk = config.get("afk", {"enabled": False, "message": "I'm currently AFK"})
        self.auto_reply = config.get("auto_reply", {"enabled": False, "triggers": {}})
        self.anti_delete = config.get("anti_delete", {"enabled": False, "channel_id": ""})
        self.ai_cfg = config.get("ai", {})
        self.sniped_messages = {}
        self.edited_messages = {}
        self.start_time = None

    async def on_ready(self):
        self.start_time = datetime.now()
        print(f"""
╔══════════════════════════════════╗
║       DISCORD BOT IS READY      ║
╠══════════════════════════════════╣
║  Bot   : {self.user.name:<22}║
║  ID    : {self.user.id:<22}║
║  Guilds: {len(self.guilds):<22}║
║  Prefix: ! and ,                ║
║  AI    : {'✅ Groq Active' if self.ai_cfg.get('enabled') and ai_client else '❌ Off':<22}║
╚══════════════════════════════════╝
        """)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!help or ,help"))

bot = AIBot()

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
    em.set_footer(text=f"{bot.user.name}", icon_url=bot.user.avatar.url if bot.user.avatar else "")
    return em

async def generate_ai_response(prompt):
    if not ai_client:
        return "❌ Groq API Key is not set."
    try:
        response = await ai_client.chat.completions.create(
            model=bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": bot.ai_cfg.get("system_prompt", "You are a helpful assistant.")},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
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
    if message.author.bot:
        return

    mentioned = bot.user.mentioned_in(message)
    is_dm = isinstance(message.channel, discord.DMChannel)

    is_reply_to_bot = False
    if message.reference and message.reference.message_id:
        try:
            replied_msg = await message.channel.fetch_message(message.reference.message_id)
            if replied_msg.author.id == bot.user.id:
                is_reply_to_bot = True
        except:
            pass

    if mentioned and bot.afk["enabled"] and not is_dm:
        try: await message.reply(f"💤 The owner is currently AFK: {bot.afk['message']}")
        except: pass

    should_reply_ai = (mentioned or is_dm or is_reply_to_bot)
    
    if bot.ai_cfg.get("enabled", False) and should_reply_ai:
        content = message.content
        if not is_dm:
            content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        
        if content:
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(1.0, 2.5))
                reply = await generate_ai_response(content)
                if len(reply) > 2000: reply = reply[:1997] + "..."
                try: await message.reply(reply)
                except: pass
            return

    if bot.auto_reply["enabled"]:
        content_lower = message.content.lower().strip()
        for trigger, reply in bot.auto_reply.get("triggers", {}).items():
            if trigger.lower() in content_lower:
                try: await message.reply(reply)
                except: pass
                break

    bot.sniped_messages[message.channel.id] = {
        "content": message.content, "author": message.author,
        "time": datetime.now(), "attachments": message.attachments
    }

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot: return
    bot.edited_messages[before.channel.id] = {
        "before": before.content, "after": after.content,
        "author": before.author, "time": datetime.now()
    }

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    
    if bot.anti_delete["enabled"] and bot.anti_delete.get("channel_id"):
        log_channel = bot.get_channel(int(bot.anti_delete["channel_id"]))
        if log_channel:
            em = discord.Embed(title="🗑️ Message Deleted", color=0xff0000, timestamp=datetime.now())
            em.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
            em.add_field(name="Channel", value=f"{message.channel.mention}", inline=True)
            content = message.content or "*No text content*"
            if len(content) > 1024: content = content[:1021] + "..."
            em.add_field(name="Content", value=content, inline=False)
            try: await log_channel.send(embed=em)
            except: pass

    bot.sniped_messages[message.channel.id] = {
        "content": message.content, "author": message.author,
        "time": datetime.now(), "attachments": message.attachments
    }

# ============================================
#           COMMANDS
# ============================================
@bot.command(name="help")
async def help_cmd(ctx):
    p = ctx.prefix
    em = embed_builder("📖 Bot Commands", f"Prefix: `{p}` (Also works with `!` and `,`)")
    categories = {
        "🤖 AI (Groq)": [
            f"`{p}ask <question>` - Ask AI manually",
            f"`{p}aimodel <model>` - Change AI Model",
            f"`{p}aitoggle <on/off>` - Toggle AI auto-reply",
            f"`{p}aiprompt <text>` - Change AI personality",
            f"`{p}aiconfig` - View current AI settings",
        ],
        "🛠️ Utility": [
            f"`{p}ping` - Check latency",
            f"`{p}uptime` - Check uptime",
            f"`{p}userinfo [user]` - User info",
            f"`{p}avatar [user]` - Get avatar",
            f"`{p}about` - Bot information",
        ],
        "💬 Moderation": [
            f"`{p}purge <amount>` - Delete messages",
            f"`{p}embed <text>` - Send embed message",
        ],
        "🔥 Roast & Fun": [
            f"`{p}roast [user]` - 🔥 Savage & Toxic AI Roast",
            f"`{p}8ball <question>` - Magic 8ball",
            f"`{p}roll [max]` - Roll dice",
            f"`{p}coinflip` - Coin flip",
            f"`{p}rps <choice>` - Rock paper scissors",
            f"`{p}gayrate [user]` - Gay rate",
        ],
        "🔍 Snipe & Auto": [
            f"`{p}snipe` - View deleted messages",
            f"`{p}editsnipe` - View edited messages",
            f"`{p}afk <on/off/msg>` - Toggle Bot AFK",
            f"`{p}autoreply <on/off>` - Toggle keyword reply",
            f"`{p}addtrigger <t>|<r>` - Add trigger",
            f"`{p}antidelete <on/off> [ch]` - Log deleted messages",
        ],
        "⚙️ Settings": [
            f"`{p}setprefix <prefix>` - Change primary prefix",
            f"`{p}setstatus <type> <text>` - Change status",
        ],
    }
    for cat, cmds in categories.items():
        em.add_field(name=cat, value="\n".join(cmds), inline=False)
    await ctx.send(embed=em)

# --- COMMANDS AI ---
@bot.command(name="ask")
async def ask_cmd(ctx, *, question):
    async with ctx.typing():
        reply = await generate_ai_response(question)
        if len(reply) > 2000: reply = reply[:1997] + "..."
        await ctx.send(reply)

@bot.command(name="aimodel")
@commands.has_permissions(administrator=True)
async def aimodel_cmd(ctx, *, model="llama-3.3-70b-versatile"):
    bot.ai_cfg["model"] = model; config["ai"]["model"] = model
    save_config(config)
    await ctx.send(embed=embed_builder("⚙️ AI Model Changed", f"Model set to: `{model}`"))

@bot.command(name="aitoggle")
@commands.has_permissions(administrator=True)
async def aitoggle_cmd(ctx, state="on"):
    if state.lower() == "off":
        bot.ai_cfg["enabled"] = False; config["ai"]["enabled"] = False
        save_config(config); await ctx.send("🔴 AI Auto-Reply **disabled**.")
    else:
        bot.ai_cfg["enabled"] = True; config["ai"]["enabled"] = True
        save_config(config); await ctx.send("🟢 AI Auto-Reply **enabled**.")

@bot.command(name="aiprompt")
@commands.has_permissions(administrator=True)
async def aiprompt_cmd(ctx, *, new_prompt):
    bot.ai_cfg["system_prompt"] = new_prompt; config["ai"]["system_prompt"] = new_prompt
    save_config(config); await ctx.send(f"✅ System Prompt changed to:\n```{new_prompt}```")

@bot.command(name="aiconfig")
async def aiconfig_cmd(ctx):
    em = embed_builder("⚙️ AI Configuration (Groq)", 
        f"**Enabled:** {'✅' if bot.ai_cfg['enabled'] else '❌'}\n"
        f"**Model:** `{bot.ai_cfg['model']}`\n"
        f"**System Prompt:** ```{bot.ai_cfg['system_prompt']}```")
    await ctx.send(embed=em)

# --- COMMANDS UTILITY ---
@bot.command(name="ping")
async def ping_cmd(ctx):
    start = time.perf_counter(); msg = await ctx.send("🏓 Pinging...")
    end = time.perf_counter(); latency = round((end - start) * 1000)
    api_lat = round(bot.latency * 1000)
    em = embed_builder("🏓 Pong!", f"**Latency:** `{latency}ms`\n**API:** `{api_lat}ms`")
    await msg.edit(content=None, embed=em)

@bot.command(name="uptime")
async def uptime_cmd(ctx):
    await ctx.send(embed=embed_builder("⏰ Uptime", f"`{get_uptime()}`"))

@bot.command(name="about", aliases=["botinfo"])
async def about_cmd(ctx):
    em = discord.Embed(
        title="🤖 AI Groq Bot Information",
        description="An all-in-one AI-powered Discord Bot using ultra-fast Groq API. Smart, witty, and fully customizable!",
        color=0x5865F2, timestamp=datetime.now()
    )
    em.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else "")
    em.add_field(name="🧠 AI Engine", value="Groq (Llama 3 / Mixtral)", inline=True)
    em.add_field(name="🏠 Servers", value=f"{len(bot.guilds)}", inline=True)
    em.add_field(name="👥 Users", value=f"{len(bot.users)}", inline=True)
    em.add_field(name="✨ Key Features", value="• 🤖 Smart AI Chat\n• 🔥 Savage AI Roasts\n• 🔍 Snipe & Edit Snipe\n• 🛡️ Anti-Delete Logger\n• 💬 Custom Triggers", inline=False)
    await ctx.send(embed=em)

@bot.command(name="userinfo", aliases=["ui"])
async def userinfo_cmd(ctx, user: discord.Member = None):
    user = user or ctx.author
    em = discord.Embed(title=f"👤 {user}", color=user.color, timestamp=datetime.now())
    em.set_thumbnail(url=user.avatar.url if user.avatar else "")
    em.add_field(name="ID", value=user.id, inline=True)
    em.add_field(name="Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
    em.add_field(name="Joined", value=f"<t:{int(user.joined_at.timestamp())}:R>", inline=True)
    roles = [r.mention for r in user.roles[1:]] or ["None"]
    em.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles[:15]), inline=False)
    await ctx.send(embed=em)

@bot.command(name="avatar", aliases=["av"])
async def avatar_cmd(ctx, user: discord.User = None):
    user = user or ctx.author
    if not user.avatar: return await ctx.send("❌ User has no avatar!")
    await ctx.send(embed=embed_builder("🖼️ Avatar", f"[Download]({user.avatar.url})", color=0x00ff00).set_image(url=user.avatar.url))

# --- COMMANDS MODERATION ---
@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def purge_cmd(ctx, amount: int = 10):
    if amount > 100: return await ctx.send("❌ Maximum 100 messages!")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=embed_builder("🗑️ Purge", f"Successfully deleted `{len(deleted)-1}` messages!"))
    await asyncio.sleep(3); await msg.delete()

@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_cmd(ctx, *, text):
    await ctx.send(embed=embed_builder("💬 Embed Message", text, color=random.randint(0, 0xffffff)))
    await ctx.message.delete()

# --- COMMANDS SNIPE & AUTO ---
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
@commands.has_permissions(administrator=True)
async def afk_cmd(ctx, *, action="on"):
    if action.lower() in ["off", "disable"]:
        bot.afk["enabled"] = False; config["afk"]["enabled"] = False; save_config(config)
        em = embed_builder("💤 AFK", "Bot AFK **disabled**")
    elif action.lower() in ["on", "enable"]:
        bot.afk["enabled"] = True; bot.afk["message"] = "I'm currently AFK"
        config["afk"]["enabled"] = True; config["afk"]["message"] = "I'm currently AFK"; save_config(config)
        em = embed_builder("💤 AFK", "Bot AFK **enabled**")
    else:
        bot.afk["enabled"] = True; bot.afk["message"] = action
        config["afk"]["enabled"] = True; config["afk"]["message"] = action; save_config(config)
        em = embed_builder("💤 AFK", f"Bot AFK **enabled**\nMessage: `{action}`")
    await ctx.send(embed=em)

@bot.command(name="autoreply")
@commands.has_permissions(administrator=True)
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
@commands.has_permissions(administrator=True)
async def addtrigger_cmd(ctx, *, text):
    parts = text.split("|")
    if len(parts) < 2: return await ctx.send("❌ Format: `addtrigger trigger|reply`")
    trigger, reply = parts[0].strip(), "|".join(parts[1:]).strip()
    bot.auto_reply.setdefault("triggers", {})[trigger] = reply; config["auto_reply"]["triggers"][trigger] = reply
    save_config(config); await ctx.send(embed=embed_builder("✅ Trigger Added", f"`{trigger}` → `{reply}`"))

@bot.command(name="antidelete")
@commands.has_permissions(administrator=True)
async def antidelete_cmd(ctx, action="on", channel: discord.TextChannel = None):
    if action.lower() in ["off", "disable"]:
        bot.anti_delete["enabled"] = False; config["anti_delete"]["enabled"] = False; save_config(config)
        em = embed_builder("🛡️ Anti Delete", "Anti Delete **disabled**")
    else:
        ch = channel or ctx.channel; bot.anti_delete["enabled"] = True; bot.anti_delete["channel_id"] = str(ch.id)
        config["anti_delete"]["enabled"] = True; config["anti_delete"]["channel_id"] = str(ch.id); save_config(config)
        em = embed_builder("🛡️ Anti Delete", f"Anti Delete **enabled**\nLog Channel: {ch.mention}")
    await ctx.send(embed=em)

# --- COMMANDS FUN & ROAST ---
@bot.command(name="roast")
async def roast_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    
    # Kalau yang di-roast botnya sendiri
    if target.id == bot.user.id:
        return await ctx.send("Nice try, buddy. I'm the one holding the matches here. 🔥")

    if not ai_client:
        return await ctx.send("❌ Groq AI is not set up. Cannot roast.")

    async with ctx.typing():
        await asyncio.sleep(random.uniform(1.5, 3.0)) # Delay biar keliatan lagi mikir racunnya
        try:
            # Khusus Roast: System prompt diset menjadi super toxic dan menyebalkan
            response = await ai_client.chat.completions.create(
                model=bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": "You are an extremely toxic, ruthless, and savage internet troll. Your job is to roast the user brutally. Be harsh, insulting, sarcastic, and unforgiving. Use profanity (like fuck, shit, idiot, stupid) to make the roast hit harder. Make it personal based on their name. No holding back, give the most savage roast possible."},
                    {"role": "user", "content": f"Roast this person named {target.display_name}."}
                ],
                max_tokens=250,
                temperature=1.0 # Temperature tinggi biar makin gila dan kreatif racunnya
            )
            roast_text = response.choices[0].message.content
            
            em = discord.Embed(
                title=f"🔥 Savage Roast for {target.display_name} 🔥", 
                description=roast_text, 
                color=0xFF0000,
                timestamp=datetime.now()
            )
            em.set_footer(text=f"Requested by {ctx.author.display_name} | Don't take this seriously 😈")
            
            await ctx.send(target.mention, embed=em)
            
        except Exception as e:
            await ctx.send(f"❌ Failed to generate roast: `{e}`")

@bot.command(name="8ball")
async def eightball_cmd(ctx, *, question):
    responses = ["🟢 Definitely!", "🟢 Without a doubt!", "🟡 Most likely", "🟡 Try asking again", "🔴 Don't count on it!", "🔴 No way!"]
    await ctx.send(embed=embed_builder("🎱 Magic 8-Ball", f"**Question:** {question}\n**Answer:** {random.choice(responses)}"))

@bot.command(name="roll")
async def roll_cmd(ctx, max_num: int = 6):
    await ctx.send(embed=embed_builder("🎲 Dice Roll", f"Rolling 1-{max_num}...\n🎯 **{random.randint(1, max_num)}**"))

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
    await ctx.send(embed=embed_builder("✊ RPS", f"**You:** {choices[user_c]} {user_c.title()}\n**Bot:** {choices[bot_c]} {bot_c.title()}\n\n{res}"))

@bot.command(name="gayrate")
async def gayrate_cmd(ctx, user: discord.Member = None):
    user = user or ctx.author; rate = random.randint(0, 100)
    bar = "█" * int(rate/10) + "░" * (10 - int(rate/10))
    label = "Straight 😤" if rate < 30 else "Curious 💅" if rate < 60 else "Fabulous 🏳️‍🌈" if rate < 90 else "ULTRA GAY 🌈✨"
    await ctx.send(embed=embed_builder("🌈 Gay Rate", f"**{user.mention}** is {rate}% gay!\n`[{bar}]` {label}"))

# --- COMMANDS SETTINGS ---
@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def setprefix_cmd(ctx, new_prefix):
    bot.command_prefix = [new_prefix, ","]
    config["prefix"] = new_prefix
    save_config(config)
    await ctx.send(embed=embed_builder("⚙️ Prefix Changed", f"Primary prefix set to: `{new_prefix}`\n(Note: `,` will still work)"))

@bot.command(name="setstatus")
@commands.has_permissions(administrator=True)
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
    elif isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"❌ Missing argument! Check `{ctx.prefix}help`")
    elif isinstance(error, commands.MissingPermissions): await ctx.send("❌ You don't have permission to use this command!")
    else: await ctx.send(f"❌ Error: `{error}`")

if __name__ == "__main__":
    print("Starting AI Discord Bot...")
    try: bot.run(DISCORD_TOKEN)
    except discord.LoginFailure: print("❌ Invalid Bot Token! Check your Variables.")
    except Exception as e: print(f"❌ Error: {e}")
