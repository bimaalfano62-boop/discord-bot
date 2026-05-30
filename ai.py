import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import os
import asyncio
import random
import re
from openai import OpenAI

# ================= SETUP AI VIA OPENROUTER =================
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
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

    # 🔥 IMPROVE: NYARI BEBERAPA HALAMAN SEKALIGUS
    async def search(self, query):
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json"
                }
                async with session.get(API, params=params, headers=HEADERS, timeout=10) as res:
                    data = await res.json()
                    results = data["query"]["search"]
                    # Ambil top 3 judul biar konteksnya lengkap
                    return [r["title"] for r in results[:3]] if results else []
        except:
            return []

    # 🔥 IMPROVE: GABUNGIN TEKS DARI BEBERAPA HALAMAN
    async def get_data(self, titles):
        all_text = ""
        try:
            async with aiohttp.ClientSession() as session:
                for title in titles:
                    params = {
                        "action": "parse",
                        "page": title,
                        "prop": "text",
                        "format": "json"
                    }
                    async with session.get(API, params=params, headers=HEADERS, timeout=10) as res:
                        data = await res.json()

                        if "parse" in data and "text" in data["parse"]:
                            html = data["parse"]["text"]["*"]
                            soup = BeautifulSoup(html, "html.parser")
                            text = soup.get_text(separator=' ', strip=True)
                            text = re.sub(r'\s+', ' ', text)
                            if text:
                                all_text += f"\n\n--- Data from page: {title} ---\n{text.strip()}"
                            
                            # Batasin total teks biar gak kepanjangan (max 3500 karakter)
                            if len(all_text) > 3500:
                                break
        except:
            pass
        return all_text.strip() if all_text else None

    async def ai_answer(self, question, context):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "ERROR_ENV: OPENROUTER_API_KEY belum di-set di file .env lu!"

        def fetch_ai():
            try:
                # 🔥 PROMPT TANPA REGIONAL PRICING, FOKUS KATEGORI
                system_prompt = """You are a Discord bot who ONLY knows about the Roblox game 'King Legacy'.

CRITICAL ANTI-HALLUCINATION RULES:
1. Your knowledge MUST 100% come from the provided Wiki Data. 
2. DO NOT mix up King Legacy with Blox Fruits or any other game.
3. If the Wiki Data does not mention a specific item, DO NOT invent it. ONLY state what is explicitly written.
4. If the user asks for categories (e.g., "easy mythical swords", "best accessories"), LOOK through all the provided Wiki Data pages, find the items that match the category, and list them.
5. If the user asks for recommendations, give advice BASED ONLY on the stats/difficulty explicitly written in the Wiki Data.
6. If you are unsure, or the text doesn't have the answer, say: "The wiki doesn't mention this, so I'm not sure." NEVER guess.

FORMATTING RULES:
1. Be conversational, helpful, and chill.
2. Use bullet points for stats or lists: • **Category:** Value
3. NEVER use markdown tables (| or ---).
4. NEVER use horizontal rules (--- or *** or ___).
5. Keep it readable in Discord."""

                user_content = f"User's Question: {question}"
                if context:
                    user_content = f"Wiki Data:\n{context[:3500]}\n\n{user_content}"
                else:
                    user_content += "\n\n(Wiki Data: No relevant data found)"

                res = client.chat.completions.create(
                    model="openai/gpt-oss-20b", 
                    # Kalau gpt-oss error, ganti ke: model="google/gemma-2-9b-it:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.1, 
                    timeout=30, 
                    max_tokens=4096,
                    extra_headers={
                        "HTTP-Referer": "https://discordbot.com", 
                        "X-Title": "King Legacy Wiki Bot"
                    }
                )
                
                result = res.choices[0].message.content
                if result is None:
                    return "ERROR_API: AI returned empty response."
                
                result = re.sub(r'^[-=_*]{3,}$', '', result, flags=re.MULTILINE)
                result = re.sub(r'\n{3,}', '\n\n', result)
                return result.strip()
                
            except Exception as e:
                return f"ERROR_API: {type(e).__name__} - {str(e)[:200]}"

        try:
            return await asyncio.wait_for(asyncio.to_thread(fetch_ai), timeout=35.0)
        except asyncio.TimeoutError:
            return "ERROR_API: AI took too long to respond (Timeout)."

    def format_raw_text(self, text):
        text = text.replace(' • ', '\n• ')
        text = re.sub(r'([.!?])\s+', r'\1\n', text)
        return text

    async def get_image(self, title):
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "action": "query",
                    "titles": title,
                    "prop": "pageimages",
                    "format": "json",
                    "pithumbsize": 500
                }
                async with session.get(API, params=params, headers=HEADERS, timeout=10) as res:
                    data = await res.json()
                    for p in data["query"]["pages"].values():
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

        titles = await self.search(query)
        data = None
        main_title = None
        
        if titles:
            main_title = titles[0] # Ambil judul pertama buat gambar
            data = await self.get_data(titles) # Gabungin teks dari semua judul
        
        answer = await self.ai_answer(question=query, context=data)
        
        if answer.startswith("ERROR_ENV") or answer.startswith("ERROR_API"):
            embed = discord.Embed(
                title="❌ AI System Error",
                description=f"```{answer}```",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
            return

        pages = self.chunk_text(answer)
        image = await self.get_image(main_title) if main_title else None

        embeds = []
        for i, p in enumerate(pages):
            embed = discord.Embed(
                title=f"💡 {query[:50]}" if len(pages) == 1 else f"💡 {query[:50]} (Page {i+1}/{len(pages)})",
                description=p,
                color=discord.Color.green()
            )
            
            if main_title:
                embed.set_footer(text=f"Source: {', '.join(titles)}")
            else:
                embed.set_footer(text="No exact wiki match found")

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
            value="• `!question What is the best sword for PvP?`\n• `!question Easy mythical swords to craft`", 
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
