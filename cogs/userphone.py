import discord
import asyncio
import random
import re
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
            self.phone_active = False # Reset dulu
            await ctx.send(embed=self.embed_builder("📞 Userphone Auto-Chat", 
                "Auto-Chat **diaktifkan**!\n\n"
                "1. Kamu ketik `/userphone` manual untuk mulai.\n"
                "2. Begitu nyambung, bot akan auto ngobrol.\n"
                "3. Ketik `!phone off` buat matiin."))
        else:
            self.auto_chat_enabled = False
            self.phone_active = False
            await ctx.send(embed=self.embed_builder("📞 Userphone Auto-Chat", "Auto-Chat **dimatikan**."))

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. Cek fitur nyala atau nggak
        if not self.auto_chat_enabled:
            return

        # 2. Cek apakah pengirimnya Yggdrasil
        if message.author.id != YGGDRASIL_ID:
            return

        # 3. Cek apakah pesannya punya Embed
        if not message.embeds:
            return

        embed = message.embeds[0]
        
        # Gabungin semua teks di embed biar gampang dideteksi
        full_text = ""
        if embed.title: full_text += embed.title + " "
        if embed.author and embed.author.name: full_text += embed.author.name + " "
        if embed.description: full_text += embed.description + " "
        if embed.footer and embed.footer.text: full_text += embed.footer.text + " "
        
        full_text_lower = full_text.lower()

        # --- DETEKSI STATUS TELEPON ---

        # Kalau telepon nyambung
        if "connected" in full_text_lower or "you are now talking" in full_text_lower:
            self.phone_active = True
            return # Jangan balas pesan sistem

        # Kalau telepon putus
        if "hung up" in full_text_lower or "call has ended" in full_text_lower or "declined" in full_text_lower:
            self.phone_active = False
            try: await message.channel.send("📞 Telepon putus. Auto-chat berhenti.")
            except: pass
            return

        # --- LOGIC AUTO CHAT ---
        if self.phone_active and self.bot.ai_client:
            stranger_msg = ""
            
            # Cara 1: Cek di Description (Paling sering dipake Yggdrasil)
            if embed.description:
                desc = embed.description
                # Hapus bintang (**) dan prefix kayak "Stranger:" atau "Them:"
                clean_desc = re.sub(r'\*\*', '', desc) 
                clean_desc = re.sub(r'^(stranger|them|user)\s*:\s*', '', clean_desc, flags=re.IGNORECASE).strip()
                if clean_desc:
                    stranger_msg = clean_desc
            
            # Cara 2: Cek di Author Name (Kadang Author: "Stranger", Isi pesan di deskripsi)
            if not stranger_msg and embed.author and embed.author.name:
                author_name = re.sub(r'\*\*', '', embed.author.name).strip()
                if author_name.lower() in ["stranger", "them", "user"]:
                    if embed.description:
                        stranger_msg = re.sub(r'\*\*', '', embed.description).strip()
                else:
                    # Kalau author name isinya teks panjang (berarti itu pesannya)
                    stranger_msg = re.sub(r'^(stranger|them|user)\s*:\s*', '', author_name, flags=re.IGNORECASE).strip()

            # Kalau teks pesannya kosong, skip aja
            if not stranger_msg:
                return

            # Delay biar keliatan kayak manusia lagi mikir/ngetik
            await asyncio.sleep(random.uniform(3.0, 6.0))
            
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(1.0, 2.5))
                try:
                    response = await self.bot.ai_client.chat.completions.create(
                        model=self.bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
                        messages=[
                            {"role": "system", "content": "Kamu adalah manusia asli yang sedang chat di Discord Userphone. Gaya bahasamu kasual, pake bahasa gaul Indo. Jawab pendek aja 1-2 kalimat. JANGAN pernah bilang kalau kamu AI."},
                            {"role": "user", "content": stranger_msg}
                        ], max_tokens=60, temperature=0.9)
                    reply = response.choices[0].message.content
                    
                    # Kirim balasannya
                    await message.channel.send(reply)
                    
                except Exception as e:
                    print(f"Userphone Chat Error: {e}")

async def setup(bot):
    await bot.add_cog(Userphone(bot))
