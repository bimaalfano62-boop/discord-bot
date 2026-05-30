import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import os
import asyncio
import difflib
import random
from openai import OpenAI

# ================= SETUP AI GRATIS (GROQ) =================
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"), # Pastikan lu udah set env variable ini
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
    def __init__(self):
        super().__init__(timeout=180)
        self.embeds = []
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

    # Ganti interaction jadi ctx (context) untuk prefix command
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

            soup = BeautifulSoup(res["parse"]["text"]["*"], "html.parser")

            text = ""
            for tag in soup.find_all(["p", "li", "td", "th"]):
                t = tag.get_text("\n", strip=True)
                if t:
                    text += t + "\n"

            return text
        except:
            return None

    def ai_answer(self, question, context):
        try:
            system_prompt = """You are a helpful Discord bot expert in the Roblox game 'King Legacy'. 
The user will ask a question. You will be given context from the King Legacy Wiki.
Answer the user's question based ONLY on the provided context. 

CRITICAL RULES:
1. NEVER use markdown tables (no | or ---).
2. NEVER use horizontal rules or long dashes (no --- or *** or ___).
3. Format key-value pairs or stats like this: **Key:** Value
4. Use bullet points (•) for lists.
5. If the context does not contain the answer, say 'I couldn't find that info in the wiki.'
6. Keep the answer concise and easy to read in Discord."""

            res = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context from Wiki:\n{context[:3000]}\n\nUser's Question: {question}"}
                ]
            )
            return res.choices[0].message.content
        except Exception as e:
            print(f"AI Error: {e}")
            return "Failed to generate answer."

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

    # 🔥 GANTI JADI PREFIX COMMAND !question
    @commands.command(name="question", aliases=['q']) # Aliases: bisa pakai !q juga
    async def question(self, ctx, *, query: str): # Tanda * wajib biar teks kebaca semua
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
        pages = self.chunk_text(answer)

        image = self.get_image(title)

        embeds = []
        for i, p in enumerate(pages):
            embed = discord.Embed(
                title=f"💡 Answering: {query[:50]}",
                description=p,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Source: {title}")

            if image and i == 0:
                embed.set_image(url=image)

            embeds.append(embed)

        # Kasih view kalau halamannya lebih dari 1
        if len(embeds) > 1:
            view = WikiView()
            view.embeds = embeds
            await msg.edit(embed=embeds[0], view=view)
        else:
            await msg.edit(embed=embeds[0])

    # 🔥 GANTI JADI PREFIX COMMAND !help
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


async def get_item_info(name: str):
    loop = asyncio.get_event_loop()

    def fetch():
        try:
            res = requests.get(API, params={
                "action": "query",
                "list": "search",
                "srsearch": name,
                "format": "json"
            }).json()

            results = res["query"]["search"]
            if not results:
                return {"rarity": "Unknown", "price": "Unknown"}

            title = results[0]["title"]

            res2 = requests.get(API, params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json"
            }).json()

            soup = BeautifulSoup(res2["parse"]["text"]["*"], "html.parser")
            text = soup.get_text(" ", strip=True).lower()

            rarity = "Unknown"
            price = "Unknown"

            for r in ["common", "uncommon", "rare", "epic", "legendary", "mythical"]:
                if r in text:
                    rarity = r.capitalize()
                    break

            import re
            match = re.search(r'(\d+[.,]?\d*\s?[mb])', text)
            if match:
                price = match.group(1).upper()

            return {"rarity": rarity, "price": price}

        except:
            return {"rarity": "Unknown", "price": "Unknown"}

    return await loop.run_in_executor(None, fetch)


async def setup(bot):
    # Matiin default help biar gak konflik sama !help kita
    bot.remove_command("help")
    await bot.add_cog(AI(bot))
