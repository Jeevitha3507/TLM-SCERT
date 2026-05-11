from fastapi import WebSocket
from typing import Dict, List
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, post_id: int):
        await websocket.accept()
        if post_id not in self.active_connections:
            self.active_connections[post_id] = []
        self.active_connections[post_id].append(websocket)

    def disconnect(self, websocket: WebSocket, post_id: int):
        if post_id in self.active_connections:
            try:
                self.active_connections[post_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[post_id]:
                del self.active_connections[post_id]

    async def broadcast_to_post(self, post_id: int, message: dict):
        if post_id in self.active_connections:
            dead = []
            for ws in self.active_connections[post_id]:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, post_id)


manager = ConnectionManager()
