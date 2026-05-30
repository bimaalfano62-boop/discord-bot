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

    async def search(self, query):
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{query} King Legacy", 
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
            return "ERROR_ENV: OPENROUTER_API_KEY belum di-set di file .env lu!"

        def fetch_ai():
            try:
                # 🔥 PROMPT BARU: AI YANG BISA NGERANGKUM & NERANGIN
                system_prompt = """You are a friendly, helpful Discord bot expert in the Roblox game 'King Legacy'. Your knowledge comes from the provided Wiki Data.

HOW TO ANSWER:
1. If the user asks "how to" do something (e.g., "how to join/create a crew"), READ the relevant Wiki Page carefully. Piece together the mechanics, features, requirements, and costs mentioned in the text, and explain it to the user in a friendly, step-by-step way.
2. If the user asks for a CATEGORY (e.g., "easy mythical swords"), scan the Wiki Data, find matching items, and list them.
3. DO NOT mix up King Legacy with Blox Fruits or other games.
4. If the Wiki Data has absolutely zero relevant information about the topic, say: "I couldn't find info about that in the wiki bro 🤷". Otherwise, TRY YOUR BEST to explain using the available data."""

                user_content = f"User's Question: {question}"
                if context:
                    user_content = f"Wiki Data:\n{context[:4000]}\n\n{user_content}"
                else:
                    user_content += "\n\n(Wiki Data: No relevant data found)"

                res = client.chat.completions.create(
                    model="openai/gpt-oss-20b", 
                    # Kalau gpt-oss error, ganti ke: model="google/gemma-2-9b-it:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.4, # Naikin dikit biar dia lebih kreatif ngerangkum jawaban
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

            # 🔥 FIX GAMBAR: Cuma ilangin gambar kalau AI bener2 bilang gak tau
            if image and i == 0:
                if "couldn't find info" in answer.lower():
                    pass # Jangan tampilin gambar kalau gagal
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
        embed.add_field(name="✅ Good Questions", value="• `/question What is the best sword for PvP?`\n• `/question How to create a crew?`", inline=False)
        embed.add_field(name="❌ Bad Questions", value="• `/question hi`\n• `/question what is roblox`", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AI(bot))
