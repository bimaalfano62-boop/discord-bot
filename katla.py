import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import os
from openai import OpenAI

# ================= SETUP AI =================
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
# ============================================

# 🔥 FALLBACK KATA DARURAT (Kalau AI mati total)
FALLBACK_WORDS = {
    "id_easy": ["SABUN|Alat pembersih badan", "BAJAK|Alat menggarap sawah", "KAPAL|Kendaraan laut", "RAJIN|Suka bekerja keras", "LAPAR|Ingin makan"],
    "id_normal": ["KAWAN", "GATAL", "TALAN", "PAPAN", "LEBIH", "SADAR"],
    "id_hard": ["ADZAN", "FIRAS", "GYMNA", "QURBI", "XYLOT", "ZAHID"],
    "en_easy": ["APPLE|A red fruit", "BEACH|Sandy shore", "CHAIR|You sit on it", "DANCE|Move to music", "EAGLE|A big bird"],
    "en_normal": ["BRAVE", "CRANE", "FLAME", "GRAPE", "STORM", "WORLD"],
    "en_hard": ["XYLYL", "PYGMY", "QAJAQ", "ZYMES", "JINXS", "KYACK"]
}

# =========================
# GAME LOGIC
# =========================
class KatlaGame:
    def __init__(self, user_id, lang, difficulty, word_data):
        self.user_id = user_id
        self.lang = lang
        self.difficulty = difficulty
        self.won = False
        self.over = False
        self.max_guesses = 6
        self.guesses = []
        self.answer = ""
        self.clue = None

        if difficulty == "easy" and "|" in word_data:
            parts = word_data.split("|")
            self.answer = parts[0].strip().upper()
            self.clue = parts[1].strip()
        else:
            self.answer = re.sub(r'[^A-Z]', '', word_data.upper())[:5]
            self.clue = None

    def guess(self, word):
        word = word.upper()
        if len(word) != 5 or not word.isalpha():
            return None, "Kata harus 5 huruf dan hanya huruf!"

        result = ['⬛'] * 5
        answer_chars = list(self.answer)

        for i in range(5):
            if word[i] == answer_chars[i]:
                result[i] = '🟩'
                answer_chars[i] = None

        for i in range(5):
            if result[i] == '⬛' and word[i] in answer_chars:
                result[i] = '🟨'
                answer_chars[answer_chars.index(word[i])] = None

        result_str = "".join(result)
        self.guesses.append((word, result_str))

        if word == self.answer:
            self.won = True
            self.over = True
        elif len(self.guesses) >= self.max_guesses:
            self.over = True

        return result_str, None

    def get_board(self):
        board = ""
        for word, res in self.guesses:
            board += f"`{word[0]} {word[1]} {word[2]} {word[3]} {word[4]}` {res}\n"
        for _ in range(self.max_guesses - len(self.guesses)):
            board += "`_ _ _ _ _` ⬛⬛⬛⬛⬛\n"
        return board

# =========================
# DISCORD UI
# =========================
class GuessModal(discord.ui.Modal, title='✏️ Tebak Kata'):
    guess_input = discord.ui.TextInput(label='Masukkan 5 huruf', min_length=5, max_length=5)

    def __init__(self, cog, game):
        super().__init__()
        self.cog = cog
        self.game = game

    async def on_submit(self, interaction: discord.Interaction):
        result_str, error = self.game.guess(self.guess_input.value)
        if error: return await interaction.response.send_message(error, ephemeral=True)

        embed, view = self.cog.create_game_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=view)

        if self.game.over:
            msg = f"🎉 Selamat {interaction.user.mention}! Jawabannya **{self.game.answer}**!" if self.game.won else f"💀 Kalah {interaction.user.mention}! Jawabannya **{self.game.answer}**."
            await interaction.followup.send(msg)

class GameView(discord.ui.View):
    def __init__(self, cog, game):
        super().__init__(timeout=None)
        self.cog = cog
        self.game = game

    @discord.ui.button(label="✏️ Tebak", style=discord.ButtonStyle.success)
    async def guess_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id: return await interaction.response.send_message("❌ Bukan game lu!", ephemeral=True)
        if self.game.over: return await interaction.response.send_message("❌ Game udah selesai.", ephemeral=True)
        await interaction.response.send_modal(GuessModal(self.cog, self.game))

    @discord.ui.button(label="💡 Clue", style=discord.ButtonStyle.primary)
    async def clue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id: return await interaction.response.send_message("❌ Bukan game lu!", ephemeral=True)
        if self.game.difficulty != "easy": return await interaction.response.send_message("❌ Clue cuma buat mode Easy!", ephemeral=True)
        if not self.game.clue: return await interaction.response.send_message("❌ Clue gaada!", ephemeral=True)
        await interaction.response.send_message(f"💡 **Clue:** {self.game.clue}", ephemeral=True)

class DifficultyView(discord.ui.View):
    def __init__(self, cog, lang):
        super().__init__(timeout=None)
        self.cog = cog
        self.lang = lang

    @discord.ui.button(label="🟢 Easy", style=discord.ButtonStyle.success)
    async def easy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_game(interaction, "easy")

    @discord.ui.button(label="🟡 Normal", style=discord.ButtonStyle.secondary)
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_game(interaction, "normal")

    @discord.ui.button(label="🔴 Hard", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_game(interaction, "hard")

    async def start_game(self, interaction, difficulty):
        await interaction.response.defer() # Defer dulu biar gak timeout
        
        word_data = await self.cog.generate_word(self.lang, difficulty)
        
        # 🔥 KALO AI GAGAL, PAKAI FALLBACK DARURAT
        if not word_data:
            fallback_key = f"{self.lang}_{difficulty}"
            word_data = random.choice(FALLBACK_WORDS.get(fallback_key, ["KAWAN|Teman", "BRAVE|Berani"]))
            await interaction.followup.send("⚠️ AI lagi down nih, pakai kata dari database darurat aja ya!", ephemeral=True)

        game = KatlaGame(interaction.user.id, self.lang, difficulty, word_data)
        self.cog.active_games[interaction.user.id] = game

        embed, view = self.cog.create_game_embed(game)
        await interaction.message.edit(embed=embed, view=view)

class LanguageView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="🇮🇩 Indonesia", style=discord.ButtonStyle.primary)
    async def indo(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🇮🇩 Pilih Difficulty", description="Mau mode susah apa gampang?", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=DifficultyView(self.cog, "id"))

    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.secondary)
    async def eng(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🇬🇧 Select Difficulty", description="How hard do you want it?", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=DifficultyView(self.cog, "en"))

# =========================
# COG
# =========================
class Katla(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    # 🔥 AI WORD GENERATOR (FIXED MODEL & TIMEOUT)
    async def generate_word(self, lang, difficulty):
        def fetch():
            try:
                if lang == "id":
                    if difficulty == "easy":
                        prompt = "Generate a common 5-letter Indonesian word and a short clue. Format exactly like this: WORD|Clue. Example: SABUN|Alat pembersih badan. Reply with ONLY the format."
                    elif difficulty == "normal":
                        prompt = "Generate a common 5-letter Indonesian word. Reply with ONLY the word. Example: KAWAN"
                    else: # hard
                        prompt = "Generate a rare or obscure 5-letter Indonesian word from KBBI. Reply with ONLY the word. Example: ADZAN"
                else: # en
                    if difficulty == "easy":
                        prompt = "Generate a common 5-letter English word and a short clue. Format exactly like this: WORD|Clue. Example: APPLE|A red fruit. Reply with ONLY the format."
                    elif difficulty == "normal":
                        prompt = "Generate a common 5-letter English word. Reply with ONLY the word. Example: BRAVE"
                    else: # hard
                        prompt = "Generate a rare or obscure 5-letter English word. Reply with ONLY the word. Example: XYLYL"

                res = client.chat.completions.create(
                    model="google/gemma-2-9b-it:free", # 🔥 GANTI MODEL YANG PALING STABIL & GRATIS
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1.0, 
                    max_tokens=20,
                    extra_headers={"HTTP-Referer": "https://discordbot.com", "X-Title": "Katla Game"}
                )
                return res.choices[0].message.content.strip().upper()
            except Exception as e:
                print(f"AI Katla Error: {e}")
                return None

        try:
            # 🔥 TINGKATIN TIMEOUT JADI 20 DETIK
            return await asyncio.wait_for(asyncio.to_thread(fetch), timeout=20.0)
        except asyncio.TimeoutError:
            print("AI Katla Timeout")
            return None

    def create_game_embed(self, game):
        color = discord.Color.green() if game.won else (discord.Color.red() if game.over else discord.Color.blue())
        lang_flag = "🇮🇩" if game.lang == "id" else "🇬🇧"
        diff_emoji = {"easy": "🟢", "normal": "🟡", "hard": "🔴"}[game.difficulty]

        embed = discord.Embed(title=f"🟩 KATLA {lang_flag} {diff_emoji}", color=color)
        embed.description = game.get_board()
        
        footer = f"Sisa: {game.max_guesses - len(game.guesses)}/6"
        if game.difficulty == "easy" and not game.over:
            footer += " | Klik 💡 Clue untuk bantuan"
        embed.set_footer(text=footer)

        view = GameView(self, game)
        if game.difficulty != "easy":
            for child in view.children:
                if child.label == "💡 Clue": child.disabled = True

        if game.over:
            for child in view.children: child.disabled = True

        return embed, view

    @app_commands.command(name="katla", description="Mainkan Katla (Wordle ID/EN) - AI Generated!")
    async def katla(self, interaction: discord.Interaction):
        if interaction.user.id in self.active_games and not self.active_games[interaction.user.id].over:
            return await interaction.response.send_message("❌ Masih ada game aktif!", ephemeral=True)

        embed = discord.Embed(title="🌍 Pilih Bahasa / Select Language", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, view=LanguageView(self))

import random # Jangan lupa import random di atas

async def setup(bot: commands.Bot):
    await bot.add_cog(Katla(bot))
