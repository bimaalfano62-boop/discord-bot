import discord
import json
import os
import asyncio
import random
import sys
from datetime import datetime
from discord.ext import commands
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config_data):
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

config = load_config()

if not DISCORD_TOKEN:
    print("❌ Bot Token not found!")
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
        self.config = config
        self.save_config = save_config
        self.ai_client = ai_client
        self.afk = config.get("afk", {"enabled": False, "message": "I'm currently AFK"})
        self.auto_reply = config.get("auto_reply", {"enabled": False, "triggers": {}})
        self.anti_delete = config.get("anti_delete", {"enabled": False, "channel_id": ""})
        self.ai_cfg = config.get("ai", {})
        self.sniped_messages = {}
        self.edited_messages = {}
        self.start_time = None

    async def setup_hook(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded Cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")

    async def on_ready(self):
        self.start_time = datetime.now()
        print(f"""
╔══════════════════════════════════╗
║       DISCORD BOT IS READY      ║
╠══════════════════════════════════╣
║  Bot   : {self.user.name:<22}║
║  Prefix: ! and ,                ║
╚══════════════════════════════════╝
        """)
        status_cfg = config.get("status", {})
        if status_cfg.get("text"):
            act = discord.Activity(type=discord.ActivityType.listening, name=status_cfg["text"])
            await self.change_presence(activity=act)

bot = AIBot()

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
                try:
                    response = await bot.ai_client.chat.completions.create(
                        model=bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
                        messages=[
                            {"role": "system", "content": bot.ai_cfg.get("system_prompt", "You are a helpful assistant.")},
                            {"role": "user", "content": content}
                        ],
                        max_tokens=400, temperature=0.8
                    )
                    reply = response.choices[0].message.content
                    if len(reply) > 2000: reply = reply[:1997] + "..."
                    await message.reply(reply)
                except Exception as e:
                    await message.reply(f"❌ AI Error: `{e}`")
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

if __name__ == "__main__":
    print("Starting AI Discord Bot...")
    try: bot.run(DISCORD_TOKEN)
    except discord.LoginFailure: print("❌ Invalid Bot Token! Check your Variables.")
    except Exception as e: print(f"❌ Error: {e}")
