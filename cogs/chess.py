import discord
import chess as chess_lib
import aiohttp
import asyncio
import os
from discord.ext import commands
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Coba import library stockfish
try:
    from stockfish import Stockfish
    STOCKFISH_PY_INSTALLED = True
except ImportError:
    STOCKFISH_PY_INSTALLED = False

class ChessGame:
    def __init__(self, white: discord.Member, black: discord.Member, is_bot_game=False, engine=None):
        self.board = chess_lib.Board()
        self.white = white
        self.black = black
        self.is_bot_game = is_bot_game
        self.engine = engine

    def get_board_text(self):
        board_str = self.board.unicode(invert_color=False)
        rows = board_str.split('\n')
        final_str = "  a b c d e f g h\n"
        for i, row in enumerate(rows):
            final_str += f"{8 - i} {row} {8 - i}\n"
        final_str += "  a b c d e f g h\n"
        
        turn = "⚪ White" if self.board.turn == chess_lib.WHITE else "⚫ Black"
        return f"```{final_str}```\n**Turn:** {turn}"

    def make_move(self, move_str):
        try:
            move = self.board.parse_san(move_str)
            self.board.push(move)
            return True, None
        except ValueError as e:
            return False, str(e)

class Chess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # DETEKSI LOKASI STOCKFISH
        if os.path.exists("/usr/games/stockfish"):
            self.stockfish_path = "/usr/games/stockfish" # Khusus Railway/Linux apt-get
        elif os.name == 'nt':
            self.stockfish_path = "stockfish.exe" # Windows
        else:
            self.stockfish_path = "stockfish" # Mac / Linux biasa
        
        self.stockfish_available = False
        if STOCKFISH_PY_INSTALLED:
            try:
                test_engine = Stockfish(path=self.stockfish_path, depth=1)
                self.stockfish_available = True
                print(f"✅ Stockfish engine found at {self.stockfish_path}!")
            except Exception as e:
                print(f"⚠️ Stockfish executable not found: {e}")
                self.stockfish_available = False

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    def get_stockfish_engine(self, elo=1350):
        if not self.stockfish_available: return None
        try:
            engine = Stockfish(path=self.stockfish_path, depth=10)
            engine.set_elo_rating(elo)
            return engine
        except: return None

    # ============================================
    #           COMMANDS
    # ============================================
    @commands.group(name="chess", invoke_without_command=True)
    async def chess(self, ctx):
        pve_status = "✅ Available" if self.stockfish_available else "❌ Stockfish not installed"
        em = self.embed_builder("♟️ Chess Commands", "Play chess directly in Discord!")
        p = ctx.prefix
        em.add_field(name="Player vs Player", value=f"`{p}chess start @user`", inline=False)
        em.add_field(name=f"Player vs Bot ({pve_status})", value=f"`{p}chess play [elo]` - Default ELO: 1350\n`{p}chess setelo <elo>`", inline=False)
        em.add_field(name="Controls", value=f"`{p}chess move <e2e4>`\n`{p}chess board`\n`{p}chess resign`", inline=False)
        em.add_field(name="Fun", value=f"`{p}chess puzzle` - Daily Lichess puzzle", inline=False)
        await ctx.send(embed=em)

    # ============================================
    #           PLAYER VS PLAYER
    # ============================================
    @chess.command(name="start")
    async def start_pvp(self, ctx, opponent: discord.Member):
        if ctx.channel.id in self.games: return await ctx.send("❌ Game already running here!")
        if opponent.id == ctx.author.id: return await ctx.send("❌ You can't play against yourself!")
        if opponent.id == self.bot.user.id: return await ctx.send("❌ Use `.chess play` to play against the Bot!")
        
        game = ChessGame(white=ctx.author, black=opponent)
        self.games[ctx.channel.id] = game
        
        em = self.embed_builder("♟️ PvP Game Started!", f"**⚪ White:** {ctx.author.mention}\n**⚫ Black:** {opponent.mention}")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(opponent.mention, embed=em)

    # ============================================
    #           PLAYER VS BOT
    # ============================================
    @chess.command(name="play")
    async def start_pve(self, ctx, elo: int = 1350):
        if not self.stockfish_available:
            return await ctx.send("❌ Stockfish engine is not installed! PvP only.")
        if ctx.channel.id in self.games: return await ctx.send("❌ Game already running here!")
        
        elo = max(100, min(3200, elo))
        engine = self.get_stockfish_engine(elo)
        if not engine: return await ctx.send("❌ Failed to start engine.")

        game = ChessGame(white=ctx.author, black=self.bot.user, is_bot_game=True, engine=engine)
        self.games[ctx.channel.id] = game
        
        em = self.embed_builder("🤖 PvE Game Started!", f"**⚪ White (You):** {ctx.author.mention}\n**⚫ Black (Bot):** {self.bot.user.mention}\n**Bot ELO:** {elo}")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(embed=em)

    @chess.command(name="setelo")
    async def set_elo(self, ctx, elo: int):
        game = self.games.get(ctx.channel.id)
        if not game or not game.is_bot_game: return await ctx.send("❌ No Bot game active here.")
        elo = max(100, min(3200, elo))
        game.engine.set_elo_rating(elo)
        await ctx.send(embed=self.embed_builder("⚙️ ELO Changed", f"Bot ELO set to **{elo}**"))

    # ============================================
    #           MOVE LOGIC
    # ============================================
    @chess.command(name="move")
    async def make_move(self, ctx, *, move_str):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("❌ No active game here.")

        if game.board.turn == chess_lib.WHITE and ctx.author.id != game.white.id:
            return await ctx.send(f"❌ It's {game.white.mention}'s turn!")
        if game.board.turn == chess_lib.BLACK and ctx.author.id != game.black.id and not game.is_bot_game:
            return await ctx.send(f"❌ It's {game.black.mention}'s turn!")

        success, error = game.make_move(move_str)
        if not success: return await ctx.send(f"❌ Invalid move! Reason: `{error}`")

        result = ""
        if game.board.is_checkmate():
            winner = game.white if game.board.turn == chess_lib.BLACK else game.black
            result = f"🏆 **Checkmate! {winner.mention} wins!**"
            del self.games[ctx.channel.id]
        elif game.board.is_stalemate():
            result = "🤝 **Stalemate! Draw.**"; del self.games[ctx.channel.id]
        elif game.board.is_check():
            result = "⚠️ **Check!**"

        em = self.embed_builder("♟️ Move Made", f"**Move:** `{move_str}`\n{result}")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(embed=em)

        # ============================================
        # BOT TURN (STOCKFISH ENGINE)
        # ============================================
        if game.is_bot_game and game.board.turn == chess_lib.BLACK and not game.board.is_game_over():
            status_msg = await ctx.send("🤖 **Bot is thinking...**")
            loop = asyncio.get_event_loop()
            try:
                game.engine.set_fen_position(game.board.fen())
                best_move = await loop.run_in_executor(self.executor, game.engine.get_best_move)
                
                if best_move:
                    game.make_move(best_move)
                    result_bot = ""
                    if game.board.is_checkmate():
                        result_bot = "🏆 **Checkmate! Bot wins!**"; del self.games[ctx.channel.id]
                    elif game.board.is_stalemate():
                        result_bot = "🤝 **Stalemate! Draw.**"; del self.games[ctx.channel.id]
                    elif game.board.is_check():
                        result_bot = "⚠️ **Check!**"

                    em_bot = self.embed_builder("🤖 Bot Moved", f"**Move:** `{best_move}`\n{result_bot}")
                    em_bot.add_field(name="Board", value=game.get_board_text(), inline=False)
                    await status_msg.edit(content=None, embed=em_bot)
                else:
                    await status_msg.edit(content="❌ Bot couldn't find a move.")
            except Exception as e:
                await status_msg.edit(content=f"❌ Engine Error: `{e}`")

    @chess.command(name="board")
    async def show_board(self, ctx):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("❌ No active game here.")
        opponent = f"Bot (ELO: {game.engine.get_elo_rating()})" if game.is_bot_game else game.black.mention
        em = self.embed_builder("♟️ Current Board", f"**⚪ White:** {game.white.mention}\n**⚫ Black:** {opponent}")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(embed=em)

    @chess.command(name="resign")
    async def resign_game(self, ctx):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("❌ No active game here.")
        if ctx.author.id != game.white.id and not (game.is_bot_game and ctx.author.id == game.white.id):
            return await ctx.send("❌ You are not in this game!")
        
        winner = game.black if ctx.author.id == game.white.id else game.white
        winner_name = f"Bot" if winner.id == self.bot.user.id else winner.mention
        del self.games[ctx.channel.id]
        await ctx.send(embed=self.embed_builder("🏳️ Resigned", f"{ctx.author.mention} resigned. {winner_name} wins!"))

    # ============================================
    #           DAILY PUZZLE
    # ============================================
    @chess.command(name="puzzle")
    async def daily_puzzle(self, ctx):
        url = "https://lichess.org/api/puzzle/daily"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: return await ctx.send("❌ Failed to fetch puzzle.")
                data = await resp.json()

        puzzle = data.get("puzzle", {})
        em = self.embed_builder("🧩 Daily Chess Puzzle", f"**Rating:** {puzzle.get('glicko', {}).get('rating', 'N/A')}\n**Play:** [Lichess Daily](https://lichess.org/training/daily)")
        try:
            fen = puzzle.get("fen")
            if fen:
                board = chess_lib.Board(fen)
                em.add_field(name="Position", value=f"```{board.unicode(invert_color=True)}```", inline=False)
        except: pass
        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(Chess(bot))
