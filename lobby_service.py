from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid

class Lobby(BaseModel):
    id: str
    creator_id: str
    players: List[str]

class LobbyCreate(BaseModel):
    creator_id: str

class LobbyJoin(BaseModel):
    player_id: str

class GameLobby:
    def __init__(self, id: str, creator_id: str):
        self.id = id
        self.creator_id = creator_id
        self.players: List[str] = [creator_id]

class LobbyService:
    def __init__(self):
        self.lobbies: Dict[str, GameLobby] = {}
        self.player_service = None

    def set_player_service(self, player_service):
        self.player_service = player_service

    def create_lobby(self, creator_id: str) -> Lobby:
        # Проверяем, не находится ли игрок уже в каком-то лобби
        for lobby in self.lobbies.values():
            if creator_id in lobby.players:
                raise ValueError("Игрок уже находится в лобби")

        lobby_id = str(uuid.uuid4())
        lobby = GameLobby(lobby_id, creator_id)
        self.lobbies[lobby_id] = lobby
        return Lobby(id=lobby_id, creator_id=creator_id, players=lobby.players)

    def get_lobbies(self) -> List[Lobby]:
        return [
            Lobby(id=lobby.id, creator_id=lobby.creator_id, players=lobby.players)
            for lobby in self.lobbies.values()
        ]

    def get_lobby(self, lobby_id: str) -> Optional[Lobby]:
        lobby = self.lobbies.get(lobby_id)
        if lobby:
            return Lobby(id=lobby.id, creator_id=lobby.creator_id, players=lobby.players)
        return None

    async def join_lobby(self, lobby_id: str, player_id: str) -> Optional[Lobby]:
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return None

        # Проверяем, не находится ли игрок уже в каком-то лобби
        for existing_lobby in self.lobbies.values():
            if player_id in existing_lobby.players and existing_lobby.id != lobby_id:
                raise ValueError("Игрок уже находится в другом лобби")

        if len(lobby.players) >= 2:
            raise ValueError("Лобби уже заполнено")

        if player_id not in lobby.players:
            lobby.players.append(player_id)

            # Если лобби заполнено, уведомляем всех игроков
            if len(lobby.players) == 2 and self.player_service:
                await self.player_service.notify_lobby_full(lobby_id)

        return Lobby(id=lobby.id, creator_id=lobby.creator_id, players=lobby.players)

    def leave_lobby(self, lobby_id: str, player_id: str):
        lobby = self.lobbies.get(lobby_id)
        if lobby and player_id in lobby.players:
            lobby.players.remove(player_id)
            if not lobby.players:  # Если в лобби не осталось игроков
                del self.lobbies[lobby_id]

    def remove_player(self, player_id: str):
        for lobby_id in list(self.lobbies.keys()):
            if player_id in self.lobbies[lobby_id].players:
                self.lobbies[lobby_id].players.remove(player_id)
                if not self.lobbies[lobby_id].players:
                    del self.lobbies[lobby_id] 