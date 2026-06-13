import discord
import chess as chess_lib
import aiohttp
import asyncio
import os
from discord.ext import commands
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from stockfish import Stockfish
    STOCKFISH_PY_INSTALLED = True
except ImportError:
    STOCKFISH_PY_INSTALLED = False

try:
    import chess.svg
    import cairosvg
    IMAGE_MODE = True
except ImportError:
    IMAGE_MODE = False

# ============================================
# UI DROPDOWN MENU (PILIH GERAKAN)
# ============================================
class MoveSelectView(discord.ui.View):
    def __init__(self, cog, game, player_id):
        super().__init__(timeout=120) # Dropdown hilang setelah 2 menit tidak dipencet
        self.cog = cog
        self.game = game
        self.player_id = player_id
        
        # Ambil semua gerakan legal dan jadikan opsi dropdown
        legal_moves = list(self.game.board.legal_moves)
        options = []
        
        for move in legal_moves:
            san = self.game.board.san(move) # Contoh: e4, Nf3, Bxe5
            uci = move.uci()                # Contoh: e2e4, g1f3
            from_sq = chess_lib.square_name(move.from_square).upper()
            to_sq = chess_lib.square_name(move.to_square).upper()
            
            options.append(discord.SelectOption(
                label=san, 
                description=f"From {from_sq} to {to_sq}", 
                value=uci
            ))
            
            # Discord membatasi maksimal 25 opsi per dropdown
            if len(options) == 25:
                break

        # Buat Dropdown-nya
        self.select = discord.ui.Select(
            placeholder="📜 Pilih gerakanmu (Scroll down)...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        # Cek cuma pemain yang gilirannya yang boleh pencet
        if interaction.user.id != self.player_id:
            return await interaction.response.send_message("❌ Bukan giliranmu!", ephemeral=True)
        
        move_uci = self.values[0]
        
        # Disable dropdown setelah dipilih biar nggak diklik 2x
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)
        
        # Proses gerakan
        await self.cog.process_move(interaction, self.game, move_uci, interaction.user)

# ============================================
# LOGIC GAME & COG
# ============================================
class ChessGame:
    def __init__(self, white: discord.Member, black: discord.Member, is_bot_game=False, engine=None):
        self.board = chess_lib.Board()
        self.white = white
        self.black = black
        self.is_bot_game = is_bot_game
        self.engine = engine

    def get_board_image(self, channel_id):
        if not IMAGE_MODE: return None
        last_move = self.board.peek() if self.board.move_stack else None
        check_sq = self.board.king(self.board.turn) if self.board.is_check() else None
        
        svg_data = chess.svg.board(
            board=self.board, coordinates=True, size=400,
            lastmove=last_move, check=check_sq
        )
        png_data = cairosvg.svg2png(bytestring=svg_data)
        file_path = f"board_{channel_id}.png"
        with open(file_path, "wb") as f:
            f.write(png_data)
        return file_path

    def make_move(self, move_str):
        try:
            move = self.board.parse_san(move_str)
            self.board.push(move)
            return True, None
        except ValueError:
            try:
                move = self.board.parse_uci(move_str)
                self.board.push(move)
                return True, None
            except ValueError as e:
                return False, str(e)

class Chess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        if os.path.exists("/usr/games/stockfish"):
            self.stockfish_path = "/usr/games/stockfish"
        elif os.name == 'nt':
            self.stockfish_path = "stockfish.exe"
        else:
            self.stockfish_path = "stockfish"
        
        self.stockfish_available = False
        if STOCKFISH_PY_INSTALLED:
            try:
                test_engine = Stockfish(path=self.stockfish_path, depth=1)
                self.stockfish_available = True
            except: self.stockfish_available = False

    def embed_builder(self, title, description, color=0x00ff00):
        em = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        em.set_footer(text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else "")
        return em

    # Helper kirim papan
    async def send_board(self, dest, title, description, game, content=None, is_bot_turn=False):
        em = self.embed_builder(title, description)
        board_path = game.get_board_image(dest.id if isinstance(dest, discord.TextChannel) else dest.channel.id)
        view = None
        
        # Tampilkan Dropdown hanya jika game belum selesai dan BUKAN giliran bot
        if not game.board.is_game_over() and not is_bot_turn:
            current_player = game.white if game.board.turn == chess_lib.WHITE else game.black
            view = MoveSelectView(self, game, current_player.id)
        
        if board_path:
            file = discord.File(board_path, filename="board.png")
            em.set_image(url="attachment://board.png")
            if isinstance(dest, discord.Interaction):
                await dest.channel.send(content=content, embed=em, file=file, view=view)
            else:
                await dest.send(content=content, embed=em, file=file, view=view)
        else:
            em.add_field(name="Board", value="Install cairosvg untuk gambar", inline=False)
            if isinstance(dest, discord.Interaction):
                await dest.channel.send(content=content, embed=em, view=view)
            else:
                await dest.send(content=content, embed=em, view=view)

    # Core Logic gerakan (dipakai oleh Command & Dropdown)
    async def process_move(self, ctx_or_inter, game, move_str, player):
        channel = ctx_or_inter.channel if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter
        
        success, error = game.make_move(move_str)
        if not success:
            dest = ctx_or_inter.channel if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter
            return await dest.send(f"❌ Invalid move! Reason: `{error}`")

        result = ""
        if game.board.is_checkmate():
            winner = game.white if game.board.turn == chess_lib.BLACK else game.black
            result = f"🏆 **Checkmate! {winner.mention} wins!**"
            del self.games[channel.id]
        elif game.board.is_stalemate():
            result = "🤝 **Stalemate! Draw.**"; del self.games[channel.id]
        elif game.board.is_check():
            result = "⚠️ **Check!**"

        san_move = game.board.peek() # Ambil gerakan terakhir yang baru aja jalan
        await self.send_board(channel, "♟️ Move Made", f"**{player.mention} moved:** `{san_move}`\n{result}", game)

        # BOT TURN (STOCKFISH ENGINE)
        if game.is_bot_game and game.board.turn == chess_lib.BLACK and not game.board.is_game_over():
            status_msg = await channel.send("🤖 **Bot is thinking...**")
            loop = asyncio.get_running_loop()
            try:
                game.engine.set_fen_position(game.board.fen())
                best_move = await loop.run_in_executor(self.executor, game.engine.get_best_move)
                if best_move:
                    game.make_move(best_move)
                    result_bot = ""
                    if game.board.is_checkmate():
                        result_bot = "🏆 **Checkmate! Bot wins!**"; del self.games[channel.id]
                    elif game.board.is_stalemate():
                        result_bot = "🤝 **Stalemate! Draw.**"; del self.games[channel.id]
                    elif game.board.is_check():
                        result_bot = "⚠️ **Check!**"

                    await status_msg.delete()
                    await self.send_board(channel, "🤖 Bot Moved", f"**Bot moved:** `{best_move}`\n{result_bot}", game)
                else:
                    await status_msg.edit(content="❌ Bot couldn't find a move.")
            except Exception as e:
                await status_msg.edit(content=f"❌ Engine Error: `{e}`")

    # ============================================
    #           COMMANDS
    # ============================================
    @commands.group(name="chess", invoke_without_command=True)
    async def chess(self, ctx):
        pve_status = "✅ Available" if self.stockfish_available else "❌ Stockfish not installed"
        em = self.embed_builder("♟️ Chess Commands", "Play chess directly in Discord! Now with Dropdown UI!")
        p = ctx.prefix
        em.add_field(name="Player vs Player", value=f"`{p}chess start @user`", inline=False)
        em.add_field(name=f"Player vs Bot ({pve_status})", value=f"`{p}chess play [elo]` - Default ELO: 1350", inline=False)
        em.add_field(name="Controls", value="Just use the **Dropdown Menu** below the board!\nOr type `{p}chess move <e4>`", inline=False)
        await ctx.send(embed=em)

    @chess.command(name="start")
    async def start_pvp(self, ctx, opponent: discord.Member):
        if ctx.channel.id in self.games: return await ctx.send("❌ Game already running here!")
        if opponent.id == ctx.author.id: return await ctx.send("❌ You can't play against yourself!")
        if opponent.id == self.bot.user.id: return await ctx.send("❌ Use `.chess play` to play against the Bot!")
        
        game = ChessGame(white=ctx.author, black=opponent)
        self.games[ctx.channel.id] = game
        await self.send_board(ctx, "♟️ PvP Game Started!", f"**⚪ White:** {ctx.author.mention}\n**⚫ Black:** {opponent.mention}", game, content=opponent.mention)

    @chess.command(name="play")
    async def start_pve(self, ctx, elo: int = 1350):
        if not self.stockfish_available: return await ctx.send("❌ Stockfish engine is not installed!")
        if ctx.channel.id in self.games: return await ctx.send("❌ Game already running here!")
        
        elo = max(100, min(3200, elo))
        engine = self.get_stockfish_engine(elo)
        if not engine: return await ctx.send("❌ Failed to start engine.")

        game = ChessGame(white=ctx.author, black=self.bot.user, is_bot_game=True, engine=engine)
        self.games[ctx.channel.id] = game
        await self.send_board(ctx, "🤖 PvE Game Started!", f"**⚪ White (You):** {ctx.author.mention}\n**⚫ Black (Bot):** {self.bot.user.mention}\n**Bot ELO:** {elo}", game)

    @chess.command(name="move")
    async def make_move(self, ctx, *, move_str):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("❌ No active game here.")
        if game.board.turn == chess_lib.WHITE and ctx.author.id != game.white.id:
            return await ctx.send(f"❌ It's {game.white.mention}'s turn!")
        if game.board.turn == chess_lib.BLACK and ctx.author.id != game.black.id and not game.is_bot_game:
            return await ctx.send(f"❌ It's {game.black.mention}'s turn!")

        await self.process_move(ctx, game, move_str, ctx.author)

    @chess.command(name="board")
    async def show_board(self, ctx):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("❌ No active game here.")
        opponent = f"Bot (ELO: {game.engine.get_elo_rating()})" if game.is_bot_game else game.black.mention
        await self.send_board(ctx, "♟️ Current Board", f"**⚪ White:** {game.white.mention}\n**⚫ Black:** {opponent}", game)

    @chess.command(name="resign")
    async def resign_game(self, ctx):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("❌ No active game here.")
        is_white = ctx.author.id == game.white.id
        is_black = (not game.is_bot_game and ctx.author.id == game.black.id)
        if not is_white and not is_black: return await ctx.send("❌ You are not in this game!")
        
        winner = game.black if is_white else game.white
        winner_name = "Bot" if (game.is_bot_game and is_white) else winner.mention
        del self.games[ctx.channel.id]
        await ctx.send(embed=self.embed_builder("🏳️ Resigned", f"{ctx.author.mention} resigned. {winner_name} wins!"))

    def get_stockfish_engine(self, elo=1350):
        if not self.stockfish_available: return None
        try:
            engine = Stockfish(path=self.stockfish_path, depth=10)
            engine.set_elo_rating(elo)
            return engine
        except: return None

async def setup(bot):
    await bot.add_cog(Chess(bot))
