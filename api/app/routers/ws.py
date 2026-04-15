from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

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
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)


pipeline_hub = PipelineHub()


@router.websocket("/pipeline")
async def pipeline_ws(websocket: WebSocket):
    await pipeline_hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pipeline_hub.disconnect(websocket)
