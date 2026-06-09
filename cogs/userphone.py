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
            self.phone_active = False # Reset status
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

        # Gabungin semua teks dari Embed biar gampang di-scan
        full_text = ""
        for embed in message.embeds:
            if embed.author: full_text += str(embed.author.name) + " "
            if embed.title: full_text += str(embed.title) + " "
            if embed.description: full_text += str(embed.description) + " "
            for field in embed.fields:
                full_text += str(field.name) + " " + str(field.value) + " "
        
        full_text_lower = full_text.lower()

        # 1. Deteksi Telepon Putus
        if "hung up" in full_text_lower or "call has ended" in full_text_lower or "disconnected" in full_text_lower:
            self.phone_active = False
            try: await message.channel.send("📞 Telepon putus. Auto-chat berhenti.")
            except: pass
            return

        # 2. Deteksi Telepon Nyambung
        if "connected" in full_text_lower or "you are now talking" in full_text_lower:
            self.phone_active = True
            # Jangan balas pesan system "Connected", tunggu orangnya ngomong dulu
            return

        # 3. Logic Auto Chat
        if self.phone_active and self.bot.ai_client:
            # Coba ekstrak pesan dari stranger (bisa di title, description, atau field)
            stranger_msg = ""
            embed = message.embeds[0]
            
            if embed.description and len(embed.description.strip()) > 0:
                desc = embed.description
                # Bersihin dari prefix kalau ada
                for prefix in ["**stranger:**", "**them:**", "**user:**", "stranger:", "them:", "user:"]:
                    if desc.lower().startswith(prefix):
                        desc = desc[len(prefix):].strip()
                        break
                stranger_msg = desc
            elif embed.title and len(embed.title.strip()) > 0:
                stranger_msg = embed.title
            elif embed.fields:
                # Kalau ada field, ambil value dari field pertama
                stranger_msg = embed.fields[0].value
            
            # Kalau tetap kosong, skip
            if not stranger_msg or len(stranger_msg) < 1:
                return

            # Delay biar keliatan kayak manusia lagi mikir/ngetik
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
