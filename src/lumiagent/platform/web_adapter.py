"""Web platform adapter with FastAPI REST + WebSocket."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from lumiagent.logging import get_logger
from lumiagent.models.message import (
    MessageContent,
    MessageType,
    Platform,
    UnifiedMessage,
)
from lumiagent.platform.base import PlatformAdapter

logger = get_logger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        conn_id = uuid.uuid4().hex[:12]
        self._connections[conn_id] = ws
        logger.info("WebSocket connected", conn_id=conn_id)
        return conn_id

    def disconnect(self, conn_id: str) -> None:
        self._connections.pop(conn_id, None)
        logger.info("WebSocket disconnected", conn_id=conn_id)

    async def send(self, conn_id: str, data: dict[str, Any]) -> None:
        ws = self._connections.get(conn_id)
        if ws:
            await ws.send_json(data)

    async def broadcast(self, data: dict[str, Any]) -> None:
        disconnected = []
        for conn_id, ws in self._connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(conn_id)
        for conn_id in disconnected:
            self.disconnect(conn_id)


class WebAdapter(PlatformAdapter):
    """FastAPI-based web adapter with REST API and WebSocket support."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.app = FastAPI(title="LumiAgent API", version="0.1.0")
        self.connections = ConnectionManager()
        self._server_task: asyncio.Task | None = None
        self._setup_routes()

    @property
    def platform_name(self) -> Platform:
        return Platform.WEB

    def _setup_routes(self) -> None:
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @self.app.post("/api/chat")
        async def chat(body: dict[str, Any]) -> dict[str, Any]:
            text = body.get("message", "")
            user_id = body.get("user_id", "web_user")
            channel_id = body.get("channel_id", f"web_{user_id}")

            msg = UnifiedMessage.text(
                text=text,
                platform=Platform.WEB,
                channel_id=channel_id,
                user_id=user_id,
            )

            # Store a future for the response
            response_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()
            msg.metadata["_response_future"] = response_future
            await self._dispatch(msg)

            try:
                result = await asyncio.wait_for(response_future, timeout=120)
                return {"response": result}
            except asyncio.TimeoutError:
                return {"response": "Request timed out", "error": True}

        @self.app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket) -> None:
            conn_id = await self.connections.connect(ws)
            try:
                while True:
                    data = await ws.receive_json()
                    text = data.get("message", "")
                    user_id = data.get("user_id", conn_id)

                    msg = UnifiedMessage.text(
                        text=text,
                        platform=Platform.WEB,
                        channel_id=f"ws_{conn_id}",
                        user_id=user_id,
                    )
                    msg.metadata["_ws_conn_id"] = conn_id
                    await self._dispatch(msg)
            except WebSocketDisconnect:
                self.connections.disconnect(conn_id)
            except Exception:
                logger.exception("WebSocket error", conn_id=conn_id)
                self.connections.disconnect(conn_id)

    async def start(self) -> None:
        import uvicorn

        config = uvicorn.Config(
            self.app, host=self.host, port=self.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(server.serve())
        logger.info("Web adapter started", host=self.host, port=self.port)

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
        logger.info("Web adapter stopped")

    async def send_message(self, channel_id: str, content: MessageContent) -> None:
        text = content.text or ""

        if channel_id.startswith("ws_"):
            conn_id = channel_id[3:]
            await self.connections.send(conn_id, {
                "type": "message",
                "content": text,
            })
        else:
            logger.debug("REST response handled via future", channel_id=channel_id)
