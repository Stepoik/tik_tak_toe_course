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
        handler = self.message_handlers.get(message.get('type'))
        if handler:
            await handler(message)

    async def send_message(self, message: dict):
        await self.websocket.send_text(json.dumps(message))

class PlayerService:
    def __init__(self, lobby_service: LobbyService, game_service: GameService):
        self.lobby_service = lobby_service
        self.game_service = game_service
        self.players: Dict[str, Player] = {}

    async def connect_player(self, websocket: WebSocket, user_id: str):
        player = Player(user_id, websocket)
        self.players[user_id] = player

        # Регистрируем обработчики сообщений
        player.register_handler('start_game', lambda msg: self.handle_start_game(user_id, msg))
        player.register_handler('make_move', lambda msg: self.handle_make_move(user_id, msg))

        await websocket.accept()

    def disconnect_player(self, user_id: str):
        player = self.players.get(user_id)
        if player:
            # Если игрок был в лобби, удаляем его оттуда
            if player.current_lobby_id:
                self.lobby_service.leave_lobby(player.current_lobby_id, user_id)
            # Если игрок был в игре, удаляем игру
            if player.current_game_id:
                self.game_service.remove_game(player.current_game_id)
            del self.players[user_id]

    async def handle_message(self, user_id: str, message: dict):
        player = self.players.get(user_id)
        if player:
            await player.handle_message(message)

    async def handle_start_game(self, user_id: str, message: dict):
        player = self.players.get(user_id)
        if not player:
            return

        lobby_id = message.get('lobby_id')
        if not lobby_id:
            await player.send_message({'type': 'error', 'message': 'Не указан ID лобби'})
            return

        lobby = self.lobby_service.get_lobby(lobby_id)
        if not lobby:
            await player.send_message({'type': 'error', 'message': 'Лобби не найдено'})
            return

        if len(lobby.players) != 2:
            await player.send_message({'type': 'error', 'message': 'В лобби должно быть 2 игрока'})
            return

        # Создаем новую игру
        game = self.game_service.create_game(game_id=lobby.id, player1=lobby.players[0], player2=lobby.players[1])
        player.current_game_id = game.game_id

        # Отправляем состояние игры обоим игрокам
        game_state = game.get_state()
        for player_id in lobby.players:
            if player_id in self.players:
                await self.players[player_id].send_message({
                    'type': 'game_state',
                    **game_state
                })

    async def handle_make_move(self, user_id: str, message: dict):
        player = self.players.get(user_id)
        if not player:
            return

        game_id = message.get('game_id')
        if not game_id:
            await player.send_message({'type': 'error', 'message': 'Не указан ID игры'})
            return

        game = self.game_service.get_game(game_id)
        if not game:
            await player.send_message({'type': 'error', 'message': 'Игра не найдена'})
            return

        if game.current_player != user_id:
            await player.send_message({'type': 'error', 'message': 'Сейчас не ваш ход'})
            return

        row = message.get('row')
        col = message.get('col')
        if row is None or col is None:
            await player.send_message({'type': 'error', 'message': 'Не указаны координаты хода'})
            return

        if not game.make_move(user_id, row, col):
            await player.send_message({'type': 'error', 'message': 'Недопустимый ход'})
            return

        # Отправляем обновленное состояние игры обоим игрокам
        game_state = game.get_state()
        for player_id in [game.player1, game.player2]:
            if player_id in self.players:
                await self.players[player_id].send_message({
                    'type': 'game_state',
                    **game_state
                })

        # Если игра закончена, удаляем её
        if game_state['winner'] or game_state['is_draw']:
            self.game_service.remove_game(game_id)

    def get_player(self, user_id: str) -> Optional[Player]:
        return self.players.get(user_id)

    async def notify_lobby_full(self, lobby_id: str):
        """Уведомляет всех игроков в лобби о том, что оно заполнено и перенаправляет их на игру"""
        lobby = self.lobby_service.get_lobby(lobby_id)
        if not lobby or len(lobby.players) != 2:
            return

        # Создаем новую игру
        game = self.game_service.create_game(game_id=lobby.id, player1=lobby.players[0], player2=lobby.players[1])

        # Отправляем сообщение о перенаправлении всем игрокам в лобби
        for player_id in lobby.players:
            if player_id in self.players:
                player = self.players[player_id]
                player.current_game_id = game.game_id
                await player.send_message({
                    'type': 'redirect',
                    'url': f'/game.html?game_id={lobby_id}&player_id={player_id}'
                }) 