from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid

class Lobby(BaseModel):
    id: str
    players: List[str]
    is_full: bool = False

class LobbyCreate(BaseModel):
    creator_id: str

class LobbyJoin(BaseModel):
    player_id: str

class LobbyService:
    def __init__(self):
        self.lobbies: Dict[str, List[str]] = {}

    def create_lobby(self, player_id: str) -> Lobby:
        # Проверяем, не находится ли игрок уже в каком-то лобби
        if any(player_id in players for players in self.lobbies.values()):
            raise HTTPException(status_code=400, detail="Игрок уже находится в лобби")
        
        lobby_id = str(uuid.uuid4())
        self.lobbies[lobby_id] = [player_id]
        return Lobby(id=lobby_id, players=[player_id])

    def join_lobby(self, player_id: str, lobby_id: str) -> Lobby:
        # Проверяем, не находится ли игрок уже в каком-то лобби
        if any(player_id in players for players in self.lobbies.values()):
            raise HTTPException(status_code=400, detail="Игрок уже находится в лобби")

        if lobby_id not in self.lobbies:
            raise HTTPException(status_code=404, detail="Лобби не найдено")

        lobby = self.lobbies[lobby_id]
        
        # Проверяем, не пытается ли игрок присоединиться к самому себе
        if player_id in lobby:
            raise HTTPException(status_code=400, detail="Нельзя присоединиться к своему собственному лобби")

        if len(lobby) >= 2:
            raise HTTPException(status_code=400, detail="Лобби уже заполнено")

        lobby.append(player_id)
        return Lobby(id=lobby_id, players=lobby, is_full=len(lobby) >= 2)

    def get_lobbies(self) -> List[Lobby]:
        return [
            Lobby(id=lobby_id, players=players, is_full=len(players) >= 2)
            for lobby_id, players in self.lobbies.items()
        ]

    def remove_player(self, player_id: str):
        for lobby_id in list(self.lobbies.keys()):
            if player_id in self.lobbies[lobby_id]:
                self.lobbies[lobby_id].remove(player_id)
                if not self.lobbies[lobby_id]:
                    del self.lobbies[lobby_id]

    def get_lobby(self, lobby_id: str) -> Optional[Lobby]:
        if lobby_id in self.lobbies:
            return Lobby(
                id=lobby_id,
                players=self.lobbies[lobby_id],
                is_full=len(self.lobbies[lobby_id]) >= 2
            )
        return None 