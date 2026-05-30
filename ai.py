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

    # 🔥 SMART SEARCH: Clean query so Fandom doesn't get confused
    async def search(self, query):
        query_lower = query.lower()
        search_query = query
        
        # Remove specific mechanic words so Fandom searches for the ITEM, not the mechanic
        words_to_clean = ["m1", "m2", "damage", "combo", "hit", "scaling", "how much", "dps"]
        clean_query = query
        for word in words_to_clean:
            clean_query = re.sub(rf'\b{word}\b', '', clean_query, flags=re.IGNORECASE)
        clean_query = clean_query.strip()

        # Smart mapping based on context
        if any(word in query_lower for word in ["gamepass", "robux", "buy", "pass", "spend"]):
            search_query = "Gamepasses King Legacy"
        elif any(word in query_lower for word in ["crew", "guild", "team", "create crew"]):
            search_query = "Crews King Legacy"
        elif any(word in query_lower for word in ["sword", "swords", "blade", "melee"]):
            search_query = f"{clean_query} Swords King Legacy"
        elif any(word in query_lower for word in ["accessories", "accessory"]):
            search_query = f"{clean_query} Accessories King Legacy"
        elif any(word in query_lower for word in ["race", "awakening", "skill"]):
            search_query = f"{clean_query} Races King Legacy"
        elif any(word in query_lower for word in ["boss", "spawn", "drop"]):
            search_query = f"{clean_query} Bosses King Legacy"
        else:
            # Default: Use cleaned query + skills/stats to find the exact fruit/item page
            search_query = f"{clean_query} skills stats King Legacy"

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
                    return [r["title"] for r in results[:3]] if results else []
        except:
            return []

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
                            
                            for tag in soup.find_all(['sup', 'nav', 'footer']):
                                tag.decompose()
                                
                            text = soup.get_text(separator=' ', strip=True)
                            text = re.sub(r'\s+', ' ', text)
                            if text:
                                all_text += f"\n\n=== WIKI PAGE: {title} ===\n{text.strip()}"
                            
                            if len(all_text) > 4000:
                                break
        except:
            pass
        return all_text.strip() if all_text else None

    async def ai_answer(self, question, context):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "ERROR_ENV: OPENROUTER_API_KEY is not set in your .env file!"

        def fetch_ai():
            try:
                # 🔥 PROMPT: OPINIONATED & ANALYTICAL EXPERT
                system_prompt = """You are a highly analytical, pro-player Discord bot expert in the Roblox game 'King Legacy'.

HOW TO ANSWER:
1. You will be given Wiki Data. Read it carefully.
2. If the user asks about specific stats, damage (like M1 damage), or moves: Extract the exact numbers/facts from the Wiki Data, then PROVIDE YOUR OPINION AND ANALYSIS. Is the damage good for its rarity? Is it viable for PvP/PvE? Is the move slow or fast? Give your take as an expert.
3. If the user asks for recommendations, compare the items in the Wiki Data and recommend the best one based on their needs/budget, explaining WHY.
4. If the user asks "how to" do something, piece together the steps from the Wiki Data.
5. DO NOT just say "I couldn't find info" if the Wiki Data contains the relevant item page. Use logic to find the answer based on the data provided.
6. DO NOT mix up King Legacy with Blox Fruits or other games. King Legacy does NOT have V4 race awakenings.
7. ONLY say "I couldn't find info" if the Wiki Data is completely empty or has zero connection to the question.

FORMATTING RULES:
1. Be conversational, helpful, and analytical. Like a pro player giving advice.
2. Use bullet points for lists and stats: • **Stat:** Value
3. NEVER use markdown tables (| or ---).
4. NEVER use horizontal rules (--- or *** or ___).
5. Keep it readable in Discord."""

                user_content = f"User's Question: {question}"
                if context:
                    user_content = f"Wiki Data:\n{context[:4000]}\n\n{user_content}"
                else:
                    user_content += "\n\n(Wiki Data: No relevant data found)"

                res = client.chat.completions.create(
                    model="openai/gpt-oss-20b", 
                    # If gpt-oss errors, change to: model="google/gemma-2-9b-it:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.6, # Higher temperature for better opinions/analysis
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

    @discord.app_commands.command(name="question", description="Ask anything about King Legacy")
    async def question(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)
        
        titles = await self.search(query)
        data = None
        main_title = None
        
        if titles:
            main_title = titles[0]
            data = await self.get_data(titles)
        
        answer = await self.ai_answer(question=query, context=data)
        
        if answer.startswith("ERROR_ENV") or answer.startswith("ERROR_API"):
            await interaction.followup.send(f"❌ **AI Error:** ```{answer}```", ephemeral=True)
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

    @discord.app_commands.command(name="help", description="How to use the AI bot")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 King Legacy AI Bot", 
            description="This bot uses AI to answer your questions based on the official King Legacy Wiki.", 
            color=discord.Color.blue()
        )
        embed.add_field(name="❓ How to Ask", value="Use `/question <your question>`\nExample: `/question How to get Dragon Fruit?`", inline=False)
        embed.add_field(name="✅ Good Questions", value="• `/question M1 Tree Fruit damage?`\n• `/question What gamepass should I buy with 10k robux?`", inline=False)
        embed.add_field(name="❌ Bad Questions", value="• `/question hi`\n• `/question what is roblox`", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AI(bot))
