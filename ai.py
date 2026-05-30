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

            # Pakai lxml parser biar lebih bersih
            soup = BeautifulSoup(res["parse"]["text"]["*"], "lxml")

            # HAPUS SEMUA TABEL & ELEMENT YANG BIKIN BERANTAKAN
            for tag in soup.find_all(['table', 'aside', 'script', 'style', 'nav']):
                tag.decompose()

            text = ""
            for tag in soup.find_all(["p", "li"]):
                t = tag.get_text(" ", strip=True)
                if t and len(t) > 15:  # Skip baris yang terlalu pendek (kayak "399", "Bundle", dll)
                    text += t + "\n"

            # Bersihin spasi ganda & enter berlebih
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' +', ' ', text)

            return text.strip() if text else None
        except:
            return None

    # 🔥 FIXED: AI ANSWER DENGAN PROMPT SUPER KETAT
    def ai_answer(self, question, context):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ ERROR: GROQ_API_KEY belum di-set di file .env!")
            return None

        try:
            system_prompt = """You are a Discord bot that answers questions about the Roblox game 'King Legacy'.

INPUT: You will receive messy/ugly raw text scraped from the King Legacy Wiki.
TASK: Extract the relevant info to answer the user's question, then format it beautifully for Discord.

ABSOLUTE RULES (READ CAREFULLY):
1. Output ONLY Discord-friendly markdown.
2. NEVER output raw CSV, raw table data, or separated words like "Bundle" "Price" "399" on different lines.
3. Combine stats into clean key-value pairs: **Rarity:** Mythical | **Price:** 399 Robux
4. NEVER use markdown tables (no | or ---).
5. NEVER use horizontal rules (no --- or *** or ___).
6. Use bullet points (•) for lists.
7. If the text is too messy, summarize ONLY the important points.
8. Do NOT repeat the same info twice.
9. Keep it SHORT and CLEAN."""

            res = client.chat.completions.create(
                model="llama-3.1-70b-versatile", # Pakai 70b biar otaknya kuat bersihin data sampah
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Raw Wiki Text:\n{context[:3500]}\n\nUser's Question: {question}"}
                ],
                temperature=0.2 # Rendahin kreativitas biar fokus ngerapihin
            )
            
            result = res.choices[0].message.content
            
            # Post-cleaning: Kalau AI masih bandel nge-spam garis
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
                description="I couldn't find any relevant wiki page for your question.",
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
            source_text = f"Source: {title} (AI Generated)"
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
