from typing import Dict, Optional
import uuid

class Game:
    def __init__(self, game_id: str, player1: str, player2: str):
        self.game_id = game_id
        self.player1 = player1
        self.player2 = player2
        self.board = [["" for _ in range(3)] for _ in range(3)]
        self.current_player = player1
        self.winner = None
        self.is_draw = False

    def make_move(self, player: str, row: int, col: int) -> bool:
        if player != self.current_player or self.board[row][col] != "":
            return False

        self.board[row][col] = "X" if player == self.player1 else "O"

        # Проверка на победителя
        if self.check_winner():
            self.winner = player
            return True

        # Проверка на ничью
        if all(cell != "" for row in self.board for cell in row):
            self.is_draw = True
            return True

        self.current_player = self.player2 if player == self.player1 else self.player1
        return True

    def check_winner(self) -> bool:
        # Проверка по горизонтали и вертикали
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != "":
                return True
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != "":
                return True

        # Проверка по диагоналям
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != "":
            return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != "":
            return True

        return False

    def get_state(self) -> dict:
        return {
            "type": "game_state",
            "game_id": self.game_id,
            "board": self.board,
            "current_player": self.current_player,
            "winner": self.winner,
            "is_draw": self.is_draw
        }

class GameService:
    def __init__(self):
        self.games: Dict[str, Game] = {}

    def create_game(self, player1: str, player2: str) -> Game:
        game_id = str(uuid.uuid4())
        game = Game(game_id, player1, player2)
        self.games[game_id] = game
        return game

    def get_game(self, game_id: str) -> Optional[Game]:
        return self.games.get(game_id)

    def make_move(self, game_id: str, player: str, row: int, col: int) -> bool:
        game = self.get_game(game_id)
        if not game:
            return False
        return game.make_move(player, row, col)

    def remove_game(self, game_id: str):
        if game_id in self.games:
            del self.games[game_id]