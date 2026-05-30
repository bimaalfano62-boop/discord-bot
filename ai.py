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
            return results[0]["title"] if results else None
        except:
            return None

    def get_data(self, title):
        try:
            res = requests.get(API, params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json"
            }, headers=HEADERS).json()

            if "parse" not in res or "text" not in res["parse"]:
                return None

            soup = BeautifulSoup(res["parse"]["text"]["*"], "html.parser")
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text.strip() if text else None
        except:
            return None

    # 🔥 FIXED: AI YANG NGASIH TAU ERROR LANGSUNG DI DISCORD
    def ai_answer(self, question, context):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "ERROR_ENV: GROQ_API_KEY belum di-set di file .env lu!"

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
                model="llama3-8b-8192", # Model paling stabil di Groq
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Raw Wiki Text:\n{context[:3500]}\n\nUser's Question: {question}"}
                ],
                temperature=0.6 
            )
            
            result = res.choices[0].message.content
            result = re.sub(r'^[-=_*]{3,}$', '', result, flags=re.MULTILINE)
            result = re.sub(r'\n{3,}', '\n\n', result)
            
            return result.strip()
            
        except Exception as e:
            # Langsung return errornya biar muncul di Discord
            return f"ERROR_API: {type(e).__name__} - {str(e)[:200]}"

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
        if not data:
            await msg.edit(embed=discord.Embed(
                title="❌ Scrape Failed",
                description="Bot berhasil nemu halaman wiki, tapi gagal baca isinya.",
                color=discord.Color.red()
            ))
            return

        answer = self.ai_answer(question=query, context=data)
        
        # 🔥 CEK KALO AI ERROR
        if answer.startswith("ERROR_ENV") or answer.startswith("ERROR_API"):
            embed = discord.Embed(
                title="❌ AI System Error",
                description=f"```{answer}```\n\n**Falling back to raw wiki...**",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
            
            # Kirim raw wiki sebagai fallback
            raw_text = data[:1500]
            raw_embed = discord.Embed(
                title=f"📄 Raw: {title}",
                description=raw_text,
                color=discord.Color.orange()
            )
            image = self.get_image(title)
            if image: raw_embed.set_image(url=image)
            
            await ctx.send(embed=raw_embed)
            return

        # Kalau AI sukses
        pages = self.chunk_text(answer)
        image = self.get_image(title)

        embeds = []
        for i, p in enumerate(pages):
            embed = discord.Embed(
                title=f"💡 {query[:50]}",
                description=p,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Source: {title}")

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
