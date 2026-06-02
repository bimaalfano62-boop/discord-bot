import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import re
import os
import google.generativeai as genai

# ================= SETUP AI (GOOGLE GEMINI) =================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Kunci untuk queue (tanpa fallback words)
VALID_KEYS = ["id_easy", "id_normal", "id_hard", "en_easy", "en_normal", "en_hard"]
# ==========================================================

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
            self.clue = parts[1].strip() if len(parts) > 1 else None
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
        try:
            result_str, error = self.game.guess(self.guess_input.value)
            if error:
                return await interaction.response.send_message(error, ephemeral=True)

            embed, view = self.cog.create_game_embed(self.game)
            await interaction.response.edit_message(embed=embed, view=view)

            if self.game.over:
                msg = f"🎉 Selamat {interaction.user.mention}! Jawabannya **{self.game.answer}**!" if self.game.won else f"💀 Kalah {interaction.user.mention}! Jawabannya **{self.game.answer}**."
                await interaction.followup.send(msg)
        except Exception as e:
            print(f"[GuessModal Error] {e}")

class GameView(discord.ui.View):
    def __init__(self, cog, game):
        super().__init__(timeout=600.0)
        self.cog = cog
        self.game = game

        for child in self.children:
            if child.custom_id == "surrender_btn":
                child.label = "🏳️ Menyerah" if game.lang == "id" else "🏳️ Surrender"

        if game.difficulty != "easy":
            for child in self.children:
                if child.custom_id == "clue_btn":
                    child.disabled = True

        if game.over:
            self.disable_all_buttons()

    def disable_all_buttons(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        self.disable_all_buttons()
        try:
            if self.message:
                embed = self.message.embeds[0]
                embed.color = discord.Color.dark_grey()
                embed.set_footer(text="⏰ Waktu habis! Game expired.")
                await self.message.edit(embed=embed, view=self)
        except: pass

    @discord.ui.button(label="✏️ Tebak", style=discord.ButtonStyle.success, custom_id="guess_btn")
    async def guess_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Bukan game lu!", ephemeral=True)
        if self.game.over:
            return await interaction.response.send_message("❌ Game udah selesai.", ephemeral=True)
        await interaction.response.send_modal(GuessModal(self.cog, self.game))

    @discord.ui.button(label="💡 Clue", style=discord.ButtonStyle.primary, custom_id="clue_btn")
    async def clue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Bukan game lu!", ephemeral=True)
        if self.game.difficulty != "easy":
            return await interaction.response.send_message("❌ Clue cuma buat mode Easy!", ephemeral=True)
        if not self.game.clue:
            return await interaction.response.send_message("❌ Clue gaada!", ephemeral=True)
        await interaction.response.send_message(f"💡 **Clue:** {self.game.clue}", ephemeral=True)

    @discord.ui.button(label="🏳️ Menyerah", style=discord.ButtonStyle.secondary, custom_id="surrender_btn")
    async def surrender_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Bukan game lu!", ephemeral=True)
        if self.game.over:
            return await interaction.response.send_message("❌ Game udah selesai.", ephemeral=True)

        self.game.over = True
        self.game.won = False
        self.disable_all_buttons()

        embed, view = self.cog.create_game_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.followup.send(f"🏳️ {interaction.user.mention} menyerah! Jawabannya adalah **{self.game.answer}**.", ephemeral=False)

class DifficultyView(discord.ui.View):
    def __init__(self, cog, lang):
        super().__init__(timeout=180.0)
        self.cog = cog
        self.lang = lang

    @discord.ui.button(label="🟢 Easy", style=discord.ButtonStyle.success, custom_id="diff_easy")
    async def easy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_game(interaction, "easy")

    @discord.ui.button(label="🟡 Normal", style=discord.ButtonStyle.secondary, custom_id="diff_normal")
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_game(interaction, "normal")

    @discord.ui.button(label="🔴 Hard", style=discord.ButtonStyle.danger, custom_id="diff_hard")
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_game(interaction, "hard")

    async def start_game(self, interaction, difficulty):
        await interaction.response.defer()
        
        try:
            word_data = await self.cog.get_word_from_queue(self.lang, difficulty)
            
            if not word_data:
                return await interaction.edit_original_response(
                    content="❌ **AI Gagal!** Server AI sedang down atau API Key belum di-set. Coba lagi nanti.", 
                    embed=None
                )

            game = KatlaGame(interaction.user.id, self.lang, difficulty, word_data)
            self.cog.active_games[interaction.user.id] = game

            embed, view = self.cog.create_game_embed(game)
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            print(f"[start_game Error] {e}")
            await interaction.edit_original_response(content=f"❌ Gagal memulai game! Error: `{e}`", embed=None)

class LanguageView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=180.0)
        self.cog = cog

    @discord.ui.button(label="🇮🇩 Indonesia", style=discord.ButtonStyle.primary, custom_id="lang_id")
    async def indo(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🇮🇩 Pilih Difficulty", description="Mau mode susah apa gampang?", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=DifficultyView(self.cog, "id"))

    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.secondary, custom_id="lang_en")
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
        self.word_queues = {key: [] for key in VALID_KEYS}

        self.background_populate_words.start()

    @tasks.loop(minutes=5)
    async def background_populate_words(self):
        max_queue_size = 3

        for key in VALID_KEYS:
            if len(self.word_queues[key]) < max_queue_size:
                lang, diff = key.split("_")
                word = await self.generate_word_from_ai(lang, diff)
                if word:
                    self.word_queues[key].append(word)
                    print(f"[Katla BG] Added AI word to {key} queue. Size: {len(self.word_queues[key])}")

    @background_populate_words.before_loop
    async def before_background_task(self):
        await self.bot.wait_until_ready()
        print("[Katla] Background word generator started!")

    async def get_word_from_queue(self, lang, difficulty):
        key = f"{lang}_{difficulty}"

        # 1. Coba ambil dari antrian (Kalau ada stok AI)
        while self.word_queues[key]:
            word_data = self.word_queues[key].pop(0)
            clean_word = re.sub(r'[^A-Z]', '', word_data.upper().split("|")[0])
            if len(clean_word) == 5:
                print(f"[Katla] Using word from AI Queue.")
                return word_data
            else:
                print(f"[Katla] Invalid word from AI Queue: {word_data}. Discarding.")

        # 2. Kalau antrian kosong, GENERATE LANGSUNG PAKAI AI (ON-THE-FLY)
        print(f"[Katla] Queue empty for {key}, generating on the fly...")
        word_data = await self.generate_word_from_ai(lang, difficulty)
        
        if word_data:
            clean_word = re.sub(r'[^A-Z]', '', word_data.upper().split("|")[0])
            if len(clean_word) == 5:
                print(f"[Katla] Successfully generated on the fly!")
                return word_data
            else:
                print(f"[Katla] Invalid word from On-The-Fly AI: {word_data}.")

        # 3. AI down / gagal total, kembalikan None
        print(f"[Katla] AI failed completely for {key}.")
        return None

    # 🔥 AI GENERATOR (PAKAI GOOGLE GEMINI FLASH)
    async def generate_word_from_ai(self, lang, difficulty):
        def fetch():
            try:
                if lang == "id":
                    if difficulty == "easy":
                        prompt = "Generate a common 5-letter Indonesian word and a short clue. Format exactly like this: WORD|Clue. Example: SABUN|Alat pembersih badan. Reply with ONLY the format."
                    elif difficulty == "normal":
                        prompt = "Generate a common 5-letter Indonesian word. Reply with ONLY the word. Example: KAWAN"
                    else:
                        prompt = "Generate a rare or obscure 5-letter Indonesian word from KBBI. Reply with ONLY the word. Example: ADZAN"
                else:
                    if difficulty == "easy":
                        prompt = "Generate a common 5-letter English word and a short clue. Format exactly like this: WORD|Clue. Example: APPLE|A red fruit. Reply with ONLY the format."
                    elif difficulty == "normal":
                        prompt = "Generate a common 5-letter English word. Reply with ONLY the word. Example: BRAVE"
                    else:
                        prompt = "Generate a rare or obscure 5-letter English word. Reply with ONLY the word. Example: XYLYL"

                response = gemini_model.generate_content(prompt)
                return response.text.strip().upper()
            except Exception as e:
                print(f"AI Katla Error: {e}")
                return None

        try:
            return await asyncio.wait_for(asyncio.to_thread(fetch), timeout=10.0)
        except asyncio.TimeoutError:
            print("AI Katla Error: Timeout")
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
        return embed, view

    @app_commands.command(name="katla", description="Mainkan Katla (Wordle ID/EN) - AI Generated!")
    async def katla(self, interaction: discord.Interaction):
        if interaction.user.id in self.active_games and not self.active_games[interaction.user.id].over:
            return await interaction.response.send_message("❌ Masih ada game aktif!", ephemeral=True)

        embed = discord.Embed(title="🌍 Pilih Bahasa / Select Language", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, view=LanguageView(self))

async def setup(bot: commands.Bot):
    await bot.add_cog(Katla(bot))
