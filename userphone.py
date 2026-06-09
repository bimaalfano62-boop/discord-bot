import discord
import asyncio
import random
from discord.ext import commands
from datetime import datetime

# GANTI INI DENGAN ID BOT YGGDRASIL DI SERVERMU
YGGDRASIL_ID = 247283454440374274

class Userphone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.phone_active = False 
        self.auto_chat_enabled = False 

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="phone")
    @commands.has_permissions(administrator=True)
    async def phone_cmd(self, ctx, state="off"):
        if state.lower() == "on":
            self.auto_chat_enabled = True
            await ctx.send(embed=self.embed_builder("📞 Userphone Auto-Chat", 
                "Auto-Chat **diaktifkan**!\n\n"
                "Cara pakai:\n"
                "1. Kamu ketik `/userphone` manual untuk mulai telepon.\n"
                "2. Begitu nyambung, bot akan otomatis ngobrol sama orang tersebut pakai AI.\n"
                "3. Kalau mau matiin, ketik `!phone off`."))
        else:
            self.auto_chat_enabled = False
            self.phone_active = False
            await ctx.send(embed=self.embed_builder("📞 Userphone Auto-Chat", "Auto-Chat **dimatikan**."))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.auto_chat_enabled or message.author.id != YGGDRASIL_ID or not message.embeds:
            return

        embed = message.embeds[0]
        desc = str(embed.description).lower() if embed.description else ""

        if "connected" in desc or "you are now connected" in desc or "stranger" in desc:
            self.phone_active = True

        if "hung up" in desc or "the call has ended" in desc or "disconnected" in desc:
            self.phone_active = False
            return

        if self.phone_active and self.bot.ai_client:
            if "stranger:" in desc or "them:" in desc or "user:" in desc:
                stranger_msg = desc
                for prefix in ["**stranger:**", "**them:**", "**user:**", "stranger:", "them:", "user:"]:
                    if stranger_msg.startswith(prefix):
                        stranger_msg = stranger_msg.replace(prefix, "", 1).strip()
                        break
                
                if not stranger_msg: return

                await asyncio.sleep(random.uniform(3.0, 6.5))
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    try:
                        response = await self.bot.ai_client.chat.completions.create(
                            model=self.bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
                            messages=[
                                {"role": "system", "content": "You are a real human chatting on a discord userphone. You are casual, friendly, and use slang. Keep responses short (1-2 sentences). Do NOT mention you are an AI. Act like a normal person."},
                                {"role": "user", "content": stranger_msg}
                            ], max_tokens=60, temperature=0.9)
                        reply = response.choices[0].message.content
                        await message.channel.send(reply)
                    except Exception as e:
                        print(f"Userphone Chat Error: {e}")

async def setup(bot):
    await bot.add_cog(Userphone(bot))
