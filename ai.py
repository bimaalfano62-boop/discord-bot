import discord
from discord.ext import commands
from datetime import datetime

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    @commands.command(name="ask")
    async def ask_cmd(self, ctx, *, question):
        async with ctx.typing():
            try:
                response = await self.bot.ai_client.chat.completions.create(
                    model=self.bot.ai_cfg.get("model", "llama-3.3-70b-versatile"),
                    messages=[
                        {"role": "system", "content": self.bot.ai_cfg.get("system_prompt", "You are a helpful assistant.")},
                        {"role": "user", "content": question}
                    ], max_tokens=400, temperature=0.8)
                reply = response.choices[0].message.content
                if len(reply) > 2000: reply = reply[:1997] + "..."
                await ctx.send(reply)
            except Exception as e:
                await ctx.send(f"❌ AI Error: `{e}`")

    @commands.command(name="aimodel")
    @commands.has_permissions(administrator=True)
    async def aimodel_cmd(self, ctx, *, model="llama-3.3-70b-versatile"):
        self.bot.ai_cfg["model"] = model; self.bot.config["ai"]["model"] = model
        self.bot.save_config(self.bot.config)
        await ctx.send(embed=self.embed_builder("⚙️ AI Model Changed", f"Model set to: `{model}`"))

    @commands.command(name="aitoggle")
    @commands.has_permissions(administrator=True)
    async def aitoggle_cmd(self, ctx, state="on"):
        if state.lower() == "off":
            self.bot.ai_cfg["enabled"] = False; self.bot.config["ai"]["enabled"] = False
            self.bot.save_config(self.bot.config); await ctx.send("🔴 AI Auto-Reply **disabled**.")
        else:
            self.bot.ai_cfg["enabled"] = True; self.bot.config["ai"]["enabled"] = True
            self.bot.save_config(self.bot.config); await ctx.send("🟢 AI Auto-Reply **enabled**.")

    @commands.command(name="aiprompt")
    @commands.has_permissions(administrator=True)
    async def aiprompt_cmd(self, ctx, *, new_prompt):
        self.bot.ai_cfg["system_prompt"] = new_prompt; self.bot.config["ai"]["system_prompt"] = new_prompt
        self.bot.save_config(self.bot.config); await ctx.send(f"✅ System Prompt changed to:\n```{new_prompt}```")

    @commands.command(name="aiconfig")
    async def aiconfig_cmd(self, ctx):
        em = self.embed_builder("⚙️ AI Configuration (Groq)", 
            f"**Enabled:** {'✅' if self.bot.ai_cfg['enabled'] else '❌'}\n"
            f"**Model:** `{self.bot.ai_cfg['model']}`\n"
            f"**System Prompt:** ```{self.bot.ai_cfg['system_prompt']}```")
        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(AI(bot))
