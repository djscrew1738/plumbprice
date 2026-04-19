"""WebSocket hub for real-time pipeline change notifications."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
import structlog

from app.core.auth import decode_token

logger = structlog.get_logger()
router = APIRouter()


class PipelineHub:
    """Simple in-memory pub/sub for pipeline change notifications."""

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        logger.info("pipeline_ws.connect", total=len(self.connections))

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        logger.info("pipeline_ws.disconnect", total=len(self.connections))

    async def broadcast(self, event: dict):
        dead: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.warning("ws.send_failed", error=str(e))
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)


pipeline_hub = PipelineHub()


@router.websocket("/pipeline")
async def pipeline_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    """Pipeline real-time updates. Requires a valid JWT via ?token= query param."""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=4001)
            return
    except Exception as e:
        logger.warning("ws.auth_failed", error=str(e))
        await websocket.close(code=4001)
        return

    await pipeline_hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pipeline_hub.disconnect(websocket)
