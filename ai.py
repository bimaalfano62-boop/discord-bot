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

# =========================
# MODALS (POP-UP FORMS)
# =========================
class SearchItemModal(discord.ui.Modal, title='🔍 Search Item'):
    item_name = discord.ui.TextInput(
        label='What item are you looking for?',
        placeholder='e.g. Dragon Fruit, Night Blade...',
        required=True
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        query = self.item_name.value
        search_query = f"{query} King Legacy"
        
        titles = await self.cog.search(search_query)
        data = await self.cog.get_data(titles)
        answer = await self.cog.ai_answer(question=query, context=data, mode="search")
        
        await self.cog.send_response(interaction, query, answer, titles)

class CompareModal(discord.ui.Modal, title='⚔️ Compare Items'):
    items = discord.ui.TextInput(
        label='Which items to compare?',
        placeholder='e.g. Noirceur vs Night Blade...',
        required=True
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        query = self.items.value
        search_query = f"{query} King Legacy"
        
        titles = await self.cog.search(search_query)
        data = await self.cog.get_data(titles)
        answer = await self.cog.ai_answer(question=query, context=data, mode="compare")
        
        await self.cog.send_response(interaction, query, answer, titles)

class SkillDamageModal(discord.ui.Modal, title='💥 Skill / Damage'):
    query_input = discord.ui.TextInput(
        label='What skill/damage info?',
        placeholder='e.g. M1 Tree Fruit damage...',
        required=True
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        query = self.query_input.value
        search_query = f"{query} skills stats King Legacy"
        
        titles = await self.cog.search(search_query)
        data = await self.cog.get_data(titles)
        answer = await self.cog.ai_answer(question=query, context=data, mode="skill")
        
        await self.cog.send_response(interaction, query, answer, titles)


# =========================
# VIEW (DASHBOARD BUTTONS)
# =========================
class DashboardView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="🔍 Search Item", style=discord.ButtonStyle.primary)
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SearchItemModal(self.cog))

    @discord.ui.button(label="⚔️ Compare", style=discord.ButtonStyle.success)
    async def compare_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CompareModal(self.cog))

    @discord.ui.button(label="💥 Skill/Damage", style=discord.ButtonStyle.danger)
    async def skill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SkillDamageModal(self.cog))


# =========================
# PAGINATION VIEW
# =========================
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


# =========================
# COG
# =========================
class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Core Logic Functions ──────────────────────────────────
    async def search(self, search_query):
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": search_query, 
                    "format": "json"
                }
                async with session.get(API, params=params, headers=HEADERS, timeout=10) as res:
                    data = await res.json()
                    results = data["query"]["search"]
                    return [r["title"] for r in results[:5]] if results else []
        except:
            return []

    async def get_data(self, titles):
        all_text = ""
        if not titles: return None
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
                            
                            for tag in soup.find_all(['sup', 'nav', 'footer']):
                                tag.decompose()
                                
                            text = soup.get_text(separator=' ', strip=True)
                            text = re.sub(r'\s+', ' ', text)
                            if text:
                                all_text += f"\n\n=== WIKI PAGE: {title} ===\n{text.strip()}"
                            
                            if len(all_text) > 4500:
                                break
        except:
            pass
        return all_text.strip() if all_text else None

    async def ai_answer(self, question, context, mode="search"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "ERROR_ENV: OPENROUTER_API_KEY is not set in your .env file!"

        # 🔥 DYNAMIC PROMPTS BASED ON DASHBOARD BUTTON
        if mode == "compare":
            system_prompt = """You are a highly analytical, pro-player Discord bot expert in 'King Legacy'.
The user wants to COMPARE items. Find BOTH items in the Wiki Data. Compare their stats, skills, and usability for PvP/PvE. Give a clear verdict on which one wins and WHY. Be opinionated but logical. Do NOT mix up King Legacy with Blox Fruits."""
        elif mode == "skill":
            system_prompt = """You are a highly analytical, pro-player Discord bot expert in 'King Legacy'.
The user wants to know about SKILLS or DAMAGE. Extract exact numbers, scaling, and cooldowns from the Wiki Data. Analyze if the damage is good for its rarity, if the move is fast or slow, and its viability in PvP/PvE. Do NOT mix up King Legacy with Blox Fruits."""
        else: # Default search
            system_prompt = """You are a friendly, expert gamer Discord bot expert in 'King Legacy'.
The user is looking for general info about an item. Provide its stats, how to get it, and your pro-player opinion on whether it's worth using or buying. Do NOT mix up King Legacy with Blox Fruits."""

        def fetch_ai():
            try:
                user_content = f"User's Question: {question}"
                if context:
                    user_content = f"Wiki Data:\n{context[:4500]}\n\n{user_content}"
                else:
                    user_content += "\n\n(Wiki Data: No relevant data found)"

                res = client.chat.completions.create(
                    model="openai/gpt-oss-20b", 
                    # If gpt-oss errors, change to: model="google/gemma-2-9b-it:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.6, 
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

    # ── Response Sender ──────────────────────────────────
    async def send_response(self, interaction, query, answer, titles):
        if answer.startswith("ERROR_ENV") or answer.startswith("ERROR_API"):
            await interaction.followup.send(f"❌ **AI Error:** ```{answer}```", ephemeral=True)
            return

        pages = self.chunk_text(answer)
        main_title = titles[0] if titles else None
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
                if "couldn't find info" in answer.lower():
                    pass 
                else:
                    embed.set_image(url=image)

            embeds.append(embed)

        if len(embeds) > 1:
            view = WikiView(embeds)
            await interaction.followup.send(embed=embeds[0], view=view)
        else:
            await interaction.followup.send(embed=embeds[0])


    # =========================
    # COMMANDS
    # =========================
    @discord.app_commands.command(name="question", description="Ask anything about King Legacy")
    async def question(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🍇 King Legacy Wiki Dashboard",
            description="Select an option below to search the wiki using AI!",
            color=0x5865F2
        )
        embed.add_field(name="🔍 Search Item", value="Look up general info, stats, and opinions.", inline=False)
        embed.add_field(name="⚔️ Compare", value="Compare two items (e.g., Noirceur vs Night Blade).", inline=False)
        embed.add_field(name="💥 Skill/Damage", value="Look up specific move damage, scaling, and viability.", inline=False)
        
        await interaction.response.send_message(embed=embed, view=DashboardView(self), ephemeral=False)


    @discord.app_commands.command(name="help", description="How to use the AI bot")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 King Legacy AI Bot", 
            description="This bot uses AI to answer your questions based on the official King Legacy Wiki.", 
            color=discord.Color.blue()
        )
        embed.add_field(name="❓ How to Ask", value="Use `/question` to open the dashboard, then pick a category!", inline=False)
        embed.add_field(name="✅ Good Questions", value="• `/question` -> Compare -> Noirceur vs Night Blade\n• `/question` -> Skill -> M1 Tree Fruit damage", inline=False)
        embed.add_field(name="❌ Bad Questions", value="• Asking outside the dashboard categories", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AI(bot))
