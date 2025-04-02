from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List
import json
from lobby_service import LobbyService, Lobby, LobbyCreate, LobbyJoin
from game_service import GameService
from player_service import PlayerService
import uuid

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("static/lobby.html")

@app.get("/lobby.html")
async def read_lobby():
    return FileResponse("static/lobby.html")

@app.get("/game.html")
async def read_game():
    return FileResponse("static/game.html")

# Инициализация сервисов
lobby_service = LobbyService()
game_service = GameService()
player_service = PlayerService(lobby_service, game_service)
lobby_service.set_player_service(player_service)

# Хранение подключенных пользователей
connected_users: Dict[str, WebSocket] = {}


# REST API endpoints для лобби
@app.post("/api/lobbies", response_model=Lobby)
async def create_lobby(lobby: LobbyCreate):
    return lobby_service.create_lobby(lobby.creator_id)

@app.get("/api/lobbies", response_model=list[Lobby])
async def get_lobbies():
    return lobby_service.get_lobbies()

@app.get("/api/lobbies/{lobby_id}", response_model=Lobby)
async def get_lobby(lobby_id: str):
    lobby = lobby_service.get_lobby(lobby_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Лобби не найдено")
    return lobby

@app.post("/api/lobbies/{lobby_id}/join", response_model=Lobby)
async def join_lobby(lobby_id: str, join_request: LobbyJoin):
    lobby = await lobby_service.join_lobby(lobby_id, join_request.player_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Лобби не найдено")
    return lobby


# WebSocket endpoint для игры
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await player_service.connect_player(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            await player_service.handle_message(user_id, data)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await player_service.disconnect_player(user_id)


async def broadcast_game_state(game_id: str):
    game = game_service.get_game(game_id)
    if game:
        game_state = game.get_state()
        for player in [game.player1, game.player2]:
            if player in connected_users:
                await connected_users[player].send_text(json.dumps(game_state))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
