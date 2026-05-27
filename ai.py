import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
import asyncio
import difflib
from openai import OpenAI

# ================= API =================
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

API = "https://king-legacy-official.fandom.com/api.php"


# ================= VIEW =================
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


# ================= COG =================
class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= LOADING GLOBAL =================
    async def fancy_loading(self, interaction, text="Processing..."):
        embed = discord.Embed(
            title="⚡ Please wait...",
            description=f"```{text}```",
            color=discord.Color.orange()
        )
        msg = await interaction.followup.send(embed=embed)
        return msg

    # SEARCH
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

    # SUGGESTIONS
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

    # SCRAPE
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
    t = t.replace("<br>", "\n").replace("<br/>", "\n")

    if t:
        text += t + "\n"

            return text
        except:
            return None

    # AI FORMAT
    def ai_format(self, text):
        try:
            res = client.responses.create(
                model="openai/gpt-oss-20b",
                input=f"Clean and format:\n{text[:4000]}"
            )
            return res.output_text
        except:
            return text[:4000]

    # IMAGE
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

    # SPLIT TEXT
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

    # ================= COMMAND =================

    @app_commands.command(name="wiki", description="Search King Legacy Wiki")
    async def wiki(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        msg = await self.fancy_loading(interaction, "🔍 Searching Wiki...")

        title = self.search(query)

        if not title:
            sug = self.get_suggestions(query)

            embed = discord.Embed(
                title="❌ Not Found",
                description="\n".join(sug) if sug else "No suggestion",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
            return

        await msg.edit(embed=discord.Embed(
            description="📡 Fetching data...",
            color=discord.Color.orange()
        ))

        data = self.get_data(title)

        if not data:
            await msg.edit(content="❌ No data")
            return

        await msg.edit(embed=discord.Embed(
            description="🧠 AI processing...",
            color=discord.Color.orange()
        ))

        formatted = self.ai_format(data)

        pages = self.chunk_text(formatted)

        url = f"https://king-legacy-official.fandom.com/wiki/{title.replace(' ', '_')}"
        img = self.get_image(title)

        embeds = []
        for i, p in enumerate(pages):
            embed = discord.Embed(
                title=f"{title} ({i+1}/{len(pages)})",
                description=p,
                color=discord.Color.green(),
                url=url
            )
            if img:
                embed.set_thumbnail(url=img)
            embeds.append(embed)

        await msg.edit(embed=embeds[0], view=WikiView(embeds))

    @app_commands.command(name="help", description="How to use the bot")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()

        msg = await self.fancy_loading(interaction, "📘 Opening help menu...")
        await asyncio.sleep(0.5)

        embed = discord.Embed(
            title="📘 Help",
            description="How to use /wiki",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="✅ Correct",
            value="/wiki Dragon Fruit\n/wiki Shark Blade",
            inline=False
        )

        embed.add_field(
            name="❌ Wrong",
            value="/wiki dragon\n/wiki fruit",
            inline=False
        )

        embed.add_field(
            name="💡 Tips",
            value="Use full names, no abbreviations",
            inline=False
        )

        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(AI(bot))
