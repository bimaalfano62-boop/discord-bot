import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

API = "https://king-legacy-official.fandom.com/api.php"


# ================= VIEW =================
class WikiView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.index = 0

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embeds) - 1:
            self.index += 1
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)


# ================= COG =================
class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔎 SEARCH
    def search(self, query):
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }

        try:
            res = requests.get(API, params=params).json()
            results = res["query"]["search"]
            if not results:
                return None
            return results[0]["title"]
        except:
            return None

    # 📘 GET DATA (INFO + OBTAIN + SKILL DIPISAH)
    def get_data(self, title):
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json"
        }

        try:
            res = requests.get(API, params=params).json()
            html = res["parse"]["text"]["*"]

            soup = BeautifulSoup(html, "html.parser")

            info = ""
            obtain = ""
            skill = ""

            # ✅ INFO TEXT
            for tag in soup.find_all(["p", "li"]):
                t = tag.get_text(" ", strip=True)
                if t:
                    info += t + "\n"

            tables = soup.find_all("table")

            for table in tables:
                text = table.get_text(" ", strip=True).lower()

                # 🔥 OBTAIN / RARITY TABLE
                if any(x in text for x in ["rarity", "obtainment", "drop", "source", "trade"]):
                    rows = table.find_all("tr")
                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        row_text = " | ".join(col.get_text(" ", strip=True) for col in cols)
                        if row_text:
                            obtain += row_text + "\n"

                # ⚔️ SKILL TABLE
                elif any(x in text for x in ["skill", "damage", "key", "move"]):
                    rows = table.find_all("tr")
                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        row_text = " | ".join(col.get_text(" ", strip=True) for col in cols)
                        if row_text:
                            skill += row_text + "\n"

            return info[:3000], obtain[:3000], skill[:3000]

        except Exception as e:
            print(e)
            return None, None, None

    # 🤖 AI INFO
    def ai_info(self, text):
        try:
            res = client.responses.create(
                model="openai/gpt-oss-20b",
                input=f"""
Explain this King Legacy item:

{text}

Format:
- What it is
- Important info
- Short
"""
            )
            return res.output_text
        except:
            return text[:1000]

    # 🤖 AI OBTAIN
    def ai_obtain(self, text):
        try:
            res = client.responses.create(
                model="openai/gpt-oss-20b",
                input=f"""
Extract this info:

{text}

Format:
- Rarity
- Tradable
- Drop / Source
- How to obtain

Short & clean
"""
            )
            return res.output_text
        except:
            return text[:1000]

    # 🤖 AI SKILL
    def ai_skill(self, text):
        try:
            res = client.responses.create(
                model="openai/gpt-oss-20b",
                input=f"""
Extract:
- Skills
- Keybinds
- Damage

{text}
"""
            )
            return res.output_text
        except:
            return text[:1000]

    # 🖼️ IMAGE
    def get_image(self, title):
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "format": "json",
            "pithumbsize": 500
        }

        try:
            res = requests.get(API, params=params).json()
            pages = res["query"]["pages"]

            for p in pages.values():
                if "thumbnail" in p:
                    return p["thumbnail"]["source"]
        except:
            pass

        return None

    # 🚀 COMMAND
    @app_commands.command(name="wiki", description="King Legacy Wiki")
    async def wiki(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        title = self.search(query)

        if not title:
            await interaction.followup.send("❌ Not found")
            return

        info, obtain, skill = self.get_data(title)

        if not info:
            await interaction.followup.send("❌ Data kosong")
            return

        info_text = self.ai_info(info)
        obtain_text = self.ai_obtain(obtain) if obtain else "No obtain data"
        skill_text = self.ai_skill(skill) if skill else "No skill data"

        img = self.get_image(title)
        url = f"https://king-legacy-official.fandom.com/wiki/{title.replace(' ', '_')}"

        # 📄 PAGE 1
        embed1 = discord.Embed(
            title=f"📘 {title}",
            description=info_text[:1000],
            color=discord.Color.green(),
            url=url
        )

        # 📄 PAGE 2
        embed2 = discord.Embed(
            title=f"📦 {title} Info",
            description=obtain_text[:1000],
            color=discord.Color.gold(),
            url=url
        )

        # 📄 PAGE 3
        embed3 = discord.Embed(
            title=f"⚔️ {title} Skills",
            description=skill_text[:1000],
            color=discord.Color.blue(),
            url=url
        )

        if img:
            embed1.set_thumbnail(url=img)
            embed2.set_thumbnail(url=img)
            embed3.set_thumbnail(url=img)

        view = WikiView([embed1, embed2, embed3])

        await interaction.followup.send(embed=embed1, view=view)


async def setup(bot):
    await bot.add_cog(AI(bot))
