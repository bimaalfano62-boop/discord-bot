import discord
from discord.ext import commands
import asyncio

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_stock = []
        self.timer_task = None

    # =========================
    # 🧠 AMBIL AI
    # =========================
    async def get_ai(self):
        return self.bot.get_cog("AI")

    # =========================
    # ➕ ADD STOCK (PAKE AI)
    # =========================
    @commands.hybrid_command(name="addstock", description="Add fruit to stock")
    async def addstock(self, ctx, *, fruit: str):
        ai = await self.get_ai()

        if not ai:
            await ctx.send("❌ AI not loaded")
            return

        data = await ai.get_fruit_data(fruit)

        self.current_stock.append(data)

        embed = discord.Embed(
            title="✅ Stock Added",
            description=f"{data['emoji']} **{data['name']}**",
            color=discord.Color.green()
        )

        embed.add_field(name="Rarity", value=data["rarity"])
        embed.add_field(name="Price", value=f"${data['price']:,}")

        await ctx.send(embed=embed)

    # =========================
    # 📦 SHOW STOCK
    # =========================
    @commands.hybrid_command(name="stock", description="Show current stock")
    async def stock(self, ctx):
        if not self.current_stock:
            await ctx.send("📦 Stock kosong")
            return

        embed = discord.Embed(
            title="📦 Current Stock",
            color=discord.Color.orange()
        )

        for item in self.current_stock:
            embed.add_field(
                name=f"{item['emoji']} {item['name']}",
                value=f"{item['rarity']} | ${item['price']:,}",
                inline=False
            )

        await ctx.send(embed=embed)

    # =========================
    # ⏱️ TIMER (GAK DIUBAH)
    # =========================
    @commands.hybrid_command(name="settimer", description="Set auto clear stock timer (seconds)")
    async def settimer(self, ctx, seconds: int):
        if self.timer_task:
            self.timer_task.cancel()

        self.timer_task = self.bot.loop.create_task(self.stock_timer(seconds))

        await ctx.send(f"⏱️ Timer set ke {seconds} detik")

    async def stock_timer(self, seconds):
        await asyncio.sleep(seconds)
        self.current_stock.clear()


async def setup(bot):
    await bot.add_cog(Stock(bot))
