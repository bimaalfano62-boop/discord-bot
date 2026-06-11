import discord
import chess
import aiohttp
import asyncio
from discord.ext import commands
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Coba import Stockfish, kalau gagolkin artinya engine belum diinstall
try:
    from stockfish import Stockfish
    STOCKFISH_AVAILABLE = True
except ImportError:
    STOCKFISH_AVAILABLE = False

class ChessGame:
    def __init__(self, white: discord.Member, black: discord.Member, is_bot_game=False, engine=None):
        self.board = chess.Board()
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
        
        turn = "⚪ White" if self.board.turn == chess.WHITE else "⚫ Black"
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
        # Thread pool buat jalanin Stockfish biar bot Discord nggak freeze saat mikir
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.stockfish_path = "stockfish" # Default path di Linux/Mac/Railway. Kalau Windows ganti jadi "stockfish.exe"

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    def get_stockfish_engine(self, elo=1350):
        if not STOCKFISH_AVAILABLE:
            return None
        try:
            # Inisialisasi Stockfish dengan ELO spesifik
            engine = Stockfish(path=self.stockfish_path)
            engine.set_elo_rating(elo)
            return engine
        except Exception as e:
            print(f"[CHESS ERROR] Stockfish init failed: {e}")
            return None

    # ============================================
    #           COMMANDS
    # ============================================
    @commands.group(name="chess", invoke_without_command=True)
    async def chess_cmd(self, ctx):
        em = self.embed_builder("♟️ Chess Commands", "Play chess directly in Discord!")
        p = ctx.prefix
        pve_status = "✅ Available" if STOCKFISH_AVAILABLE else "❌ Stockfish not installed"
        
        em.add_field(name="Player vs Player", value=f"`{p}chess start @user` - Start PvP game", inline=False)
        em.add_field(name=f"Player vs Bot ({pve_status})", value=f"`{p}chess play [elo]` - Play vs Bot (Default ELO: 1350)\n`{p}chess setelo <elo>` - Change Bot ELO mid-game", inline=False)
        em.add_field(name="Game Controls", value=f"`{p}chess move <e2e4>` - Make a move\n`{p}chess board` - View board\n`{p}chess resign` - Resign", inline=False)
        em.add_field(name="Fun", value=f"`{p}chess puzzle` - Get daily Lichess puzzle", inline=False)
        await ctx.send(embed=em)

    # ============================================
    #           PLAYER VS PLAYER
    # ============================================
    @chess.command(name="start")
    async def start_pvp(self, ctx, opponent: discord.Member):
        if ctx.channel.id in self.games:
            return await ctx.send("❌ Game already running here! Finish or resign first.")
        if opponent.id == ctx.author.id:
            return await ctx.send("❌ You can't play against yourself!")
        if opponent.id == self.bot.user.id:
            return await ctx.send("❌ Use `.chess play` to play against the Bot!")
        
        game = ChessGame(white=ctx.author, black=opponent)
        self.games[ctx.channel.id] = game
        
        em = self.embed_builder("♟️ PvP Game Started!", f"**⚪ White:** {ctx.author.mention}\n**⚫ Black:** {opponent.mention}\n\nWhite moves first!")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(opponent.mention, embed=em)

    # ============================================
    #           PLAYER VS BOT (ELO SYSTEM)
    # ============================================
    @chess.command(name="play")
    async def start_pve(self, ctx, elo: int = 1350):
        if not STOCKFISH_AVAILABLE:
            return await ctx.send("❌ Stockfish engine is not installed on the server!")
        if ctx.channel.id in self.games:
            return await ctx.send("❌ Game already running here! Finish or resign first.")
        
        elo = max(100, min(3200, elo)) # Batas ELO 100 - 3200
        engine = self.get_stockfish_engine(elo)
        if not engine:
            return await ctx.send("❌ Failed to initialize Stockfish engine.")

        # User selalu Putih, Bot selalu Hitam
        game = ChessGame(white=ctx.author, black=self.bot.user, is_bot_game=True, engine=engine)
        self.games[ctx.channel.id] = game
        
        em = self.embed_builder("🤖 PvE Game Started!", f"**⚪ White (You):** {ctx.author.mention}\n**⚫ Black (Bot):** {self.bot.user.mention}\n**Bot ELO:** {elo}\n\nMake your move!")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(embed=em)

    @chess.command(name="setelo")
    async def set_elo(self, ctx, elo: int):
        game = self.games.get(ctx.channel.id)
        if not game or not game.is_bot_game:
            return await ctx.send("❌ No Bot game active here.")
        
        elo = max(100, min(3200, elo))
        game.engine.set_elo_rating(elo)
        await ctx.send(embed=self.embed_builder("⚙️ ELO Changed", f"Bot ELO set to **{elo}**"))

    # ============================================
    #           MOVE LOGIC
    # ============================================
    @chess.command(name="move")
    async def make_move(self, ctx, *, move_str):
        game = self.games.get(ctx.channel.id)
        if not game:
            return await ctx.send("❌ No active game here.")

        # Cek giliran
        if game.board.turn == chess.WHITE and ctx.author.id != game.white.id:
            return await ctx.send(f"❌ It's {game.white.mention}'s turn!")
        if game.board.turn == chess.BLACK and ctx.author.id != game.black.id and not game.is_bot_game:
            return await ctx.send(f"❌ It's {game.black.mention}'s turn!")

        success, error = game.make_move(move_str)
        if not success:
            return await ctx.send(f"❌ Invalid move! Reason: `{error}`")

        result = ""
        if game.board.is_checkmate():
            winner = game.white if game.board.turn == chess.BLACK else game.black
            result = f"🏆 **Checkmate! {winner.mention} wins!**"
            del self.games[ctx.channel.id]
        elif game.board.is_stalemate():
            result = "🤝 **Stalemate! Draw.**"
            del self.games[ctx.channel.id]
        elif game.board.is_check():
            result = "⚠️ **Check!**"

        em = self.embed_builder("♟️ Move Made", f"**Move:** `{move_str}`\n{result}")
        em.add_field(name="Board", value=game.get_board_text(), inline=False)
        await ctx.send(embed=em)

        # ============================================
        # BOT TURN (STOCKFISH ENGINE)
        # ============================================
        if game.is_bot_game and game.board.turn == chess.BLACK and not game.board.is_game_over():
            await ctx.send("🤖 **Bot is thinking...**")
            
            # Jalankan Stockfish di thread terpisah biar bot Discord nggak mati
            loop = asyncio.get_event_loop()
            try:
                # Set posisi papan ke Stockfish
                game.engine.set_fen_position(game.board.fen())
                # Minta Stockfish cari gerakan terbaik
                best_move = await loop.run_in_executor(self.executor, game.engine.get_best_move)
                
                if best_move:
                    game.make_move(best_move)
                    
                    result_bot = ""
                    if game.board.is_checkmate():
                        result_bot = "🏆 **Checkmate! Bot wins!**"
                        del self.games[ctx.channel.id]
                    elif game.board.is_stalemate():
                        result_bot = "🤝 **Stalemate! Draw.**"
                        del self.games[ctx.channel.id]
                    elif game.board.is_check():
                        result_bot = "⚠️ **Check!**"

                    em_bot = self.embed_builder("🤖 Bot Moved", f"**Move:** `{best_move}`\n{result_bot}")
                    em_bot.add_field(name="Board", value=game.get_board_text(), inline=False)
                    await ctx.send(embed=em_bot)
                else:
                    await ctx.send("❌ Bot couldn't find a move. Game might be over.")
            except Exception as e:
                await ctx.send(f"❌ Engine Error: `{e}`")

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
    #           DAILY PUZZLE (LICHESS API)
    # ============================================
    @chess.command(name="puzzle")
    async def daily_puzzle(self, ctx):
        url = "https://lichess.org/api/puzzle/daily"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: return await ctx.send("❌ Failed to fetch puzzle.")
                data = await resp.json()

        puzzle = data.get("puzzle", {})
        puzzle_url = "https://lichess.org/training/daily"
        rating = puzzle.get("glicko", {}).get("rating", "N/A")
        
        em = self.embed_builder("🧩 Daily Chess Puzzle", f"**Rating:** {rating}\n**Play it here:** [Lichess Daily Puzzle]({puzzle_url})")
        try:
            fen = puzzle.get("fen")
            if fen:
                board = chess.Board(fen)
                board_str = board.unicode(invert_color=True)
                em.add_field(name="Position", value=f"```{board_str}```", inline=False)
        except: pass
        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(Chess(bot))
