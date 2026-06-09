import discord
import asyncio
import random
from discord.ext import commands
from datetime import datetime

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="roast")
    async def roast_cmd(self, ctx, user: discord.Member = None):
        target = user or ctx.author
        if target.id == self.bot.user.id:
            return await ctx.send("Nice try, buddy. I'm the one holding the matches here. 🔥")
        if not self.bot.ai_client:
            return await ctx.send("❌ Groq AI is not set up. Cannot roast.")

        async with ctx.typing():
            await asyncio.sleep(random.uniform(1.5, 3.0))
            try:
                response = await self.bot.ai_client.chat.completions.create(
                    model=self.bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
                    messages=[
                        {"role": "system", "content": "You are an extremely toxic, ruthless, and savage internet troll. Roast the user brutally. Be harsh, insulting, sarcastic. Use profanity. Make it personal based on their name."},
                        {"role": "user", "content": f"Roast this person named {target.display_name}."}
                    ], max_tokens=250, temperature=1.0)
                roast_text = response.choices[0].message.content
                em = discord.Embed(title=f"🔥 Savage Roast for {target.display_name} 🔥", description=roast_text, color=0xFF0000, timestamp=datetime.now())
                em.set_footer(text=f"Requested by {ctx.author.display_name} | Don't take this seriously 😈")
                await ctx.send(target.mention, embed=em)
            except Exception as e:
                await ctx.send(f"❌ Failed to generate roast: `{e}`")

    @commands.command(name="8ball")
    async def eightball_cmd(self, ctx, *, question):
        responses = ["🟢 Definitely!", "🟢 Without a doubt!", "🟡 Most likely", "🟡 Try asking again", "🔴 Don't count on it!", "🔴 No way!"]
        await ctx.send(embed=self.embed_builder("🎱 Magic 8-Ball", f"**Question:** {question}\n**Answer:** {random.choice(responses)}"))

    @commands.command(name="roll")
    async def roll_cmd(self, ctx, max_num: int = 6):
        await ctx.send(embed=self.embed_builder("🎲 Dice Roll", f"Rolling 1-{max_num}...\n🎯 **{random.randint(1, max_num)}**"))

    @commands.command(name="coinflip", aliases=["cf"])
    async def coinflip_cmd(self, ctx):
        await ctx.send(embed=self.embed_builder("Coin Flip", random.choice(["🪙 Heads!", "🪙 Tails!"])))

    @commands.command(name="rps")
    async def rps_cmd(self, ctx, choice):
        choice = choice.lower()
        if choice not in ["rock", "paper", "scissors", "r", "p", "s"]:
            return await ctx.send("❌ Choose: rock/paper/scissors")
        choices_dict = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        norm = {"r": "rock", "p": "paper", "s": "scissors"}
        user_c = norm.get(choice, choice); bot_c = random.choice(list(choices_dict.keys()))
        if user_c == bot_c: res = "🟡 Draw!"
        elif (user_c == "rock" and bot_c == "scissors") or (user_c == "paper" and bot_c == "rock") or (user_c == "scissors" and bot_c == "paper"): res = "🟢 You Win!"
        else: res = "🔴 You Lose!"
        await ctx.send(embed=self.embed_builder("✊ RPS", f"**You:** {choices_dict[user_c]} {user_c.title()}\n**Bot:** {choices_dict[bot_c]} {bot_c.title()}\n\n{res}"))

    @commands.command(name="gayrate")
    async def gayrate_cmd(self, ctx, user: discord.Member = None):
        user = user or ctx.author; rate = random.randint(0, 100)
        bar = "█" * int(rate/10) + "░" * (10 - int(rate/10))
        label = "Straight 😤" if rate < 30 else "Curious 💅" if rate < 60 else "Fabulous 🏳️‍🌈" if rate < 90 else "ULTRA GAY 🌈✨"
        await ctx.send(embed=self.embed_builder("🌈 Gay Rate", f"**{user.mention}** is {rate}% gay!\n`[{bar}]` {label}"))

async def setup(bot):
    await bot.add_cog(Fun(bot))
