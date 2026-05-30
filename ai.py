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
    filled = int((percent / 100) * segments) # Fix bug kurung
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
                    return results[0]["title"] if results else None
        except asyncio.TimeoutError:
            print("❌ Wiki Search Timeout")
            return None
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return None

    async def get_data(self, title):
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "action": "parse",
                    "page": title,
                    "prop": "text",
                    "format": "json"
                }
                async with session.get(API, params=params, headers=HEADERS, timeout=10) as res:
                    data = await res.json()

                    if "parse" not in data or "text" not in data["parse"]:
                        return None

                    html = data["parse"]["text"]["*"]
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    return text.strip() if text else None
        except asyncio.TimeoutError:
            print("❌ Wiki Parse Timeout")
            return None
        except Exception as e:
            print(f"❌ Parse Error: {e}")
            return None

    async def ai_answer(self, question, context):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "ERROR_ENV: OPENROUTER_API_KEY belum di-set di file .env lu!"

        def fetch_ai():
            try:
                system_prompt = """You are a Discord bot that formats game wiki data into a clean info card.

INPUT: You will receive messy raw text from the King Legacy Wiki.
TASK: Extract the important stats/info and format it perfectly for Discord.

ABSOLUTE FORMATTING RULES:
1. You MUST use bullet points for EVERY piece of information.
2. Format: • **Category:** Value (Example: • **Rarity:** Legendary)
3. For skills or lists, use indented sub-bullets:
   • **Skills:**
     - [Z] Skill Name: Description
     - [X] Skill Name: Description
4. NEVER use markdown tables (| or ---).
5. NEVER use horizontal rules (--- or ***).
6. NEVER write long paragraphs. Keep it strictly point-by-point.
7. Be VERY DETAILED. List ALL skills, stats, and drops if available. Do not summarize too much.
8. If a value is missing, just skip that point."""

                res = client.chat.completions.create(
                    model="openai/gpt-oss-20b", 
                    # Kalau gpt-oss error, ganti ke: model="google/gemma-2-9b-it:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Raw Wiki Text:\n{context[:3500]}\n\nFormat this into bullet points. Be detailed."}
                    ],
                    temperature=0.2,
                    timeout=30, # Naikkin dikit timeoutnya biar AI sempat nulis panjang
                    max_tokens=4096, # 🔥 INI RAHASIANYA: Biar AI bisa nulis sampai 4000+ kata (banyak halaman)
                    extra_headers={
                        "HTTP-Referer": "https://discordbot.com", 
                        "X-Title": "King Legacy Wiki Bot"
                    }
                )
                
                result = res.choices[0].message.content
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

        title = await self.search(query)
        
        if not title:
            await msg.edit(embed=discord.Embed(
                title="❌ Not Found",
                description="Couldn't find any relevant wiki page for that, bro. 🤷",
                color=discord.Color.red()
            ))
            return

        data = await self.get_data(title)
        if not data:
            await msg.edit(embed=discord.Embed(
                title="❌ Scrape Failed",
                description="Bot berhasil nemu halaman wiki, tapi gagal baca isinya.",
                color=discord.Color.red()
            ))
            return

        answer = await self.ai_answer(question=query, context=data)
        
        if answer.startswith("ERROR_ENV") or answer.startswith("ERROR_API"):
            embed = discord.Embed(
                title="❌ AI System Error",
                description=f"```{answer}```\n\n**Using auto-formatter...**",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
            
            raw_text = self.format_raw_text(data[:1500])
            raw_embed = discord.Embed(
                title=f"📄 {title}",
                description=raw_text,
                color=discord.Color.orange()
            )
            image = await self.get_image(title)
            if image: raw_embed.set_image(url=image)
            
            await ctx.send(embed=raw_embed)
            return

        # Pecah teks per 1000 karakter buat bikin halaman
        pages = self.chunk_text(answer)
        image = await self.get_image(title)

        embeds = []
        for i, p in enumerate(pages):
            embed = discord.Embed(
                title=f"💡 {title} (Page {i+1}/{len(pages)})", # 🔥 TAMBAHIN INDIKATOR HALAMAN
                description=p,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Source: King Legacy Wiki")

            # Gamblang cuma muncul di halaman pertama
            if image and i == 0:
                embed.set_image(url=image)

            embeds.append(embed)

        # 🔥 KALO LEBIH DARI 1 HALAMAN, MUNCULIN TOMBOL NEXT
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
