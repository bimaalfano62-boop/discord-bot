import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import os
import asyncio
import random
import re
from openai import OpenAI

# ================= SETUP AI GRATIS (GROQ) =================
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)
# ==========================================================

API = "https://king-legacy-official.fandom.com/api.php"

# Wajib pakai headers biar Fandom gak nge-block bot
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}

def segmented_bar(percent: int, segments: int = 12):
    filled = int((percent / 100) * segments)
    empty = segments - filled
    return "▰" * filled + "▱" * empty

loading_logs = [
    "🔍 Scanning data...",
    "🧠 Initializing AI...",
    "📡 Syncing server...",
    "⚙️ Loading modules...",
    "📊 Processing info...",
    "🛰️ Fetching wiki...",
    "💾 Parsing content...",
    "🚀 Optimizing output...",
    "🔐 Securing response...",
    "🧬 Finalizing..."
]

class WikiView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.index = 0

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embeds) - 1:
            self.index += 1
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)


class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fancy_loading(self, ctx):
        progress = 0
        embed = discord.Embed(title="🤖 AI Thinking...", description="Starting...", color=discord.Color.orange())
        msg = await ctx.send(embed=embed)

        for i in range(8):
            progress += random.randint(8, 18)
            if progress > 100:
                progress = 100

            bar = segmented_bar(progress)
            log = random.choice(loading_logs)
            stage = "🔹 Initializing" if progress < 30 else "🔸 Processing" if progress < 70 else "🔶 Finalizing"

            embed.description = f"`{bar}` {progress}%\n\n📌 {log}\n🧭 Stage: {stage}"
            await msg.edit(embed=embed)
            await asyncio.sleep(random.uniform(0.4, 1.0))

            if progress >= 100:
                break

        return msg

    def search(self, query):
        try:
            res = requests.get(API, params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json"
            }, headers=HEADERS).json()
            results = res["query"]["search"]
            if results:
                print(f"🔎 Found title: {results[0]['title']}")
                return results[0]["title"]
            return None
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return None

    # 🔥 FIXED: SCRAPER YANG LEBIH AMAN + DEBUG
    def get_data(self, title):
        try:
            res = requests.get(API, params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json"
            }, headers=HEADERS).json()

            # Cek kalau Fandom nolak / error
            if "parse" not in res or "text" not in res["parse"]:
                print(f"❌ Fandom API Error: {res}")
                return None

            html = res["parse"]["text"]["*"]
            # Ganti lxml jadi html.parser biar lebih stabil
            soup = BeautifulSoup(html, "html.parser")

            # Ambil semua teks, gabung pake spasi
            text = soup.get_text(separator=' ', strip=True)
            
            # Bersihin spasi ganda
            text = re.sub(r'\s+', ' ', text)

            if text:
                print(f"✅ Scrape success! Length: {len(text)} characters.")
                return text
            else:
                print("⚠️ Scrape result is empty!")
                return None
                
        except Exception as e:
            print(f"❌ Scrape Exception: {e}")
            return None

    def ai_answer(self, question, context):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ ERROR: GROQ_API_KEY belum di-set di file .env!")
            return None

        try:
            system_prompt = """You are a chill, helpful Discord bot who is an expert in the Roblox game 'King Legacy'. 

Your job:
1. Read the raw text from the King Legacy Wiki (it might be messy and squished together in one line).
2. Answer the user's question based on that text.

STYLE RULES:
- Talk like a friendly gamer, NOT a robot.
- Keep it conversational and easy to read.
- Extract key info and format it cleanly. Example: **Rarity:** Mythical | **Price:** 399 Robux.
- NEVER use markdown tables (no | or ---).
- NEVER use horizontal rules (no --- or *** or ___).
- Use bullet points (•) or emojis if it helps readability.
- If the text doesn't contain the answer, just say "Couldn't find that in the wiki bro 🤷"
- Do NOT repeat the same info."""

            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Raw Wiki Text:\n{context[:3500]}\n\nUser's Question: {question}"}
                ],
                temperature=0.6 
            )
            
            result = res.choices[0].message.content
            
            # Post-cleaning kalau AI masih nge-spam garis
            result = re.sub(r'^[-=_*]{3,}$', '', result, flags=re.MULTILINE)
            result = re.sub(r'\n{3,}', '\n\n', result)
            
            return result.strip()
            
        except Exception as e:
            print(f"❌ AI ERROR DETAIL: {type(e).__name__}: {e}")
            return None

    def get_image(self, title):
        try:
            res = requests.get(API, params={
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 500
            }, headers=HEADERS).json()

            for p in res["query"]["pages"].values():
                if "thumbnail" in p:
                    return p["thumbnail"]["source"]
        except:
            pass
        return None

    def chunk_text(self, text, size=1000):
        chunks = []
        while len(text) > size:
            split = text[:size].rfind(" ")
            if split == -1:
                split = size
            chunks.append(text[:split])
            text = text[split:]
        chunks.append(text)
        return chunks

    @commands.command(name="question", aliases=['q'])
    async def question(self, ctx, *, query: str):
        msg = await self.fancy_loading(ctx)

        title = self.search(query)
        
        if not title:
            await msg.edit(embed=discord.Embed(
                title="❌ Not Found",
                description="Couldn't find any relevant wiki page for that, bro. 🤷",
                color=discord.Color.red()
            ))
            return

        data = self.get_data(title)
        answer = self.ai_answer(question=query, context=data)
        
        if answer is None:
            print("⚠️ AI Failed, using raw wiki fallback...")
            # Fallback dipercantik
            fallback_text = data[:1500] if data else "Couldn't read the wiki page. It might be empty or blocked."
            source_text = "⚠️ AI failed, showing raw wiki data"
            embed_color = discord.Color.orange()
        else:
            fallback_text = answer
            source_text = f"Source: {title}"
            embed_color = discord.Color.green()

        pages = self.chunk_text(fallback_text)
        image = self.get_image(title)

        embeds = []
        for i, p in enumerate(pages):
            embed = discord.Embed(
                title=f"💡 {query[:50]}",
                description=p,
                color=embed_color
            )
            embed.set_footer(text=source_text)

            if image and i == 0:
                embed.set_image(url=image)

            embeds.append(embed)

        if len(embeds) > 1:
            view = WikiView(embeds)
            await msg.edit(embed=embeds[0], view=view)
        else:
            await msg.edit(embed=embeds[0])

    @commands.command(name="help")
    async def help(self, ctx):
        msg = await self.fancy_loading(ctx)

        embed = discord.Embed(
            title="📘 King Legacy AI Bot", 
            description="This bot uses AI to answer your questions based on the official King Legacy Wiki.", 
            color=discord.Color.blue()
        )
        embed.add_field(
            name="❓ How to Ask", 
            value="Use `!question <your question>` or `!q <your question>`\nExample: `!question How to get Dragon Fruit?`", 
            inline=False
        )
        embed.add_field(
            name="✅ Good Questions", 
            value="• `!question What is the best sword for PvP?`\n• `!question Where to find Quake fruit?`", 
            inline=False
        )
        embed.add_field(
            name="❌ Bad Questions", 
            value="• `!question hi`\n• `!question what is roblox`", 
            inline=False
        )
        embed.add_field(
            name="💡 Tips", 
            value="Ask specific things about King Legacy! The AI will read the wiki and summarize the answer for you.", 
            inline=False
        )

        await msg.edit(embed=embed)


async def setup(bot):
    bot.remove_command("help")
    await bot.add_cog(AI(bot))
