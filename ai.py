import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
import asyncio
import difflib
import random
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

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

    async def fancy_loading(self, interaction, text="Processing..."):
        progress = 0
        embed = discord.Embed(title="🤖 AI Processing...", description="Starting...", color=discord.Color.orange())
        msg = await interaction.followup.send(embed=embed)

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

    def get_suggestions(self, query):
        try:
            res = requests.get(API, params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json"
            }).json()
            titles = [r["title"] for r in res["query"]["search"]]
            return difflib.get_close_matches(query, titles, n=3, cutoff=0.3)
        except:
            return []

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

    def ai_format(self, text):
        try:
            res = client.responses.create(
                model="openai/gpt-oss-20b",
                input=f"Clean and format:\n{text[:4000]}"
            )
            return res.output_text
        except:
            return text[:4000]

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

    @app_commands.command(name="wiki", description="Search King Legacy Wiki")
    async def wiki(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        msg = await self.fancy_loading(interaction)

        title = self.search(query)
        if not title:
            sug = self.get_suggestions(query)
            await msg.edit(embed=discord.Embed(
                title="❌ Not Found",
                description="\n".join(sug) if sug else "No suggestion",
                color=discord.Color.red()
            ))
            return

        data = self.get_data(title)
        formatted = self.ai_format(data)
        pages = self.chunk_text(formatted)

        embeds = []
        for i, p in enumerate(pages):
            embeds.append(discord.Embed(
                title=f"{title} ({i+1}/{len(pages)})",
                description=p,
                color=discord.Color.green()
            ))

        await msg.edit(embed=embeds[0], view=WikiView(embeds))

    @app_commands.command(name="help", description="How to use the bot")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        msg = await self.fancy_loading(interaction)

        embed = discord.Embed(title="📘 Help", description="How to use /wiki", color=discord.Color.blue())
        embed.add_field(name="✅ Correct", value="/wiki Dragon Fruit\n/wiki Shark Blade", inline=False)
        embed.add_field(name="❌ Wrong", value="/wiki dragon\n/wiki fruit", inline=False)
        embed.add_field(name="💡 Tips", value="Use full names", inline=False)

        await msg.edit(embed=embed)


# 🔥 CORE AI FUNCTION (ASYNC)
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
    await bot.add_cog(AI(bot))
