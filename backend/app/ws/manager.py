"""
WebSocket Connection Manager
broadcast ข้อมูล sensor real-time ไปยัง client ที่เปิด dashboard อยู่
"""

import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # device_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self._connections[device_id].append(websocket)
        logger.info(f"WS connected: device={device_id} total={len(self._connections[device_id])}")

    def disconnect(self, websocket: WebSocket, device_id: str):
        conns = self._connections.get(device_id, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info(f"WS disconnected: device={device_id} remaining={len(conns)}")

    async def broadcast(self, device_id: str, data: dict):
        """ส่งข้อมูลไปยัง client ทุกตัวที่ subscribe device_id นี้"""
        dead = []
        for ws in self._connections.get(device_id, []):
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, device_id)

    @property
    def active_count(self) -> int:
        return sum(len(v) for v in self._connections.values())


ws_manager = ConnectionManager()
