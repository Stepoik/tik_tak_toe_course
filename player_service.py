from typing import Dict, Optional, Callable
from fastapi import WebSocket
import json
from lobby_service import LobbyService
from game_service import GameService

class Player:
    def __init__(self, user_id: str, websocket: WebSocket):
        self.user_id = user_id
        self.websocket = websocket
        self.current_game_id: Optional[str] = None
        self.current_lobby_id: Optional[str] = None
        self.message_handlers: Dict[str, Callable] = {}

    def register_handler(self, message_type: str, handler: Callable):
        self.message_handlers[message_type] = handler

    async def handle_message(self, message: dict):
        message_type = message.get("type")
        if message_type in self.message_handlers:
            await self.message_handlers[message_type](message)

    async def send_message(self, message: dict):
        await self.websocket.send_text(json.dumps(message))

class PlayerService:
    def __init__(self, lobby_service: LobbyService, game_service: GameService):
        self.lobby_service = lobby_service
        self.game_service = game_service
        self.players: Dict[str, Player] = {}

    async def connect_player(self, user_id: str, websocket: WebSocket) -> Player:
        player = Player(user_id, websocket)
        self.players[user_id] = player
        
        # Регистрируем обработчики сообщений
        player.register_handler("start_game", self.handle_start_game)
        player.register_handler("make_move", self.handle_make_move)
        
        return player

    def disconnect_player(self, user_id: str):
        if user_id in self.players:
            player = self.players[user_id]
            if player.current_lobby_id:
                self.lobby_service.remove_player(user_id)
            if player.current_game_id:
                game = self.game_service.get_game(player.current_game_id)
                if game:
                    self.game_service.remove_game(player.current_game_id)
            del self.players[user_id]

    async def handle_start_game(self, message: dict):
        player = self.players[message["user_id"]]
        lobby_id = message["lobby_id"]
        lobby = self.lobby_service.get_lobby(lobby_id)
        
        if lobby and len(lobby.players) == 2:
            game = self.game_service.create_game(lobby.players[0], lobby.players[1])
            player.current_game_id = game.game_id
            await self.broadcast_game_state(game.game_id)
            self.lobby_service.remove_player(player.user_id)

    async def handle_make_move(self, message: dict):
        player = self.players[message["user_id"]]
        game_id = message["game_id"]
        
        if game_id == player.current_game_id:
            if self.game_service.make_move(game_id, player.user_id, message["row"], message["col"]):
                await self.broadcast_game_state(game_id)

    async def broadcast_game_state(self, game_id: str):
        game = self.game_service.get_game(game_id)
        if game:
            game_state = game.get_state()
            for player_id in [game.player1, game.player2]:
                if player_id in self.players:
                    await self.players[player_id].send_message(game_state)

    def get_player(self, user_id: str) -> Optional[Player]:
        return self.players.get(user_id) 