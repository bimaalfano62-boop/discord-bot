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
            }).json()
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
            }).json()

            soup = BeautifulSoup(res["parse"]["text"]["*"], "lxml")

            # Hapus element sampah doang, jangan terlalu agresif ngefilter teks
            for tag in soup.find_all(['table', 'aside', 'script', 'style', 'nav']):
                tag.decompose()

            text = ""
            for tag in soup.find_all(["p", "li"]):
                t = tag.get_text(" ", strip=True)
                if t:
                    text += t + "\n"

            # Bersihin spasi ganda
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' +', ' ', text)

            return text.strip() if text else None
        except:
            return None

    # 🔥 FIXED: AI YANG SANTAI & NGALIR
    def ai_answer(self, question, context):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ ERROR: GROQ_API_KEY belum di-set di file .env!")
            return None

        try:
            system_prompt = """You are a chill, helpful Discord bot who is an expert in the Roblox game 'King Legacy'. 

Your job:
1. Read the messy raw wiki text provided.
2. Answer the user's question based on that text.

STYLE RULES:
- Talk like a friendly gamer, NOT a robot or Wikipedia article.
- Keep it conversational, relaxed, and easy to read.
- Combine messy stats into clean formats (e.g., **Rarity:** Mythical | **Price:** 399 Robux).
- NEVER use markdown tables (no | or ---).
- NEVER use horizontal rules (no --- or *** or ___).
- Use bullet points (•) or emojis if it helps readability.
- If the text doesn't contain the answer, just say "Couldn't find that in the wiki bro 🤷"
- Do NOT repeat the same info."""

            res = client.chat.completions.create(
                model="llama-3.1-8b-instant", # Kembali ke 8b biar super kenceng & jarang timeout
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Raw Wiki Text:\n{context[:3500]}\n\nUser's Question: {question}"}
                ],
                temperature=0.6 # Naikin dikiti biar gaya bahasanya lebih natural/santai
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
            }).json()

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
            answer = data[:1500] if data else "No data found."
            source_text = "⚠️ AI failed, showing raw wiki data"
            embed_color = discord.Color.orange()
        else:
            source_text = f"Source: {title}"
            embed_color = discord.Color.green()

        pages = self.chunk_text(answer)
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
