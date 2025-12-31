import asyncio
import json
import logging
from typing import Any, Dict, Set

import websockets

log = logging.getLogger(__name__)


class UiWebSocketHub:
    def __init__(
        self,
        send_timeout_sec: float = 1.5,
        max_queue: int = 32,
    ):
        self.clients: Set = set()
        self._lock = asyncio.Lock()
        self.send_timeout_sec = float(send_timeout_sec)
        self.max_queue = int(max_queue)

    async def handler(self, ws, *args, **kwargs):
        async with self._lock:
            self.clients.add(ws)

        try:
            async for _ in ws:
                pass
        except Exception as e:
            log.debug("WS client disconnected: %r", e)
        finally:
            async with self._lock:
                self.clients.discard(ws)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        msg = json.dumps(payload, ensure_ascii=False)

        async with self._lock:
            clients_snapshot = list(self.clients)

        if not clients_snapshot:
            return

        async def _safe_send(ws):
            try:
                await asyncio.wait_for(
                    ws.send(msg),
                    timeout=self.send_timeout_sec,
                )
                return True
            except Exception:
                return False

        results = await asyncio.gather(
            *(_safe_send(ws) for ws in clients_snapshot),
            return_exceptions=False,
        )

        dead = [ws for ws, ok in zip(clients_snapshot, results) if not ok]
        if dead:
            async with self._lock:
                for ws in dead:
                    self.clients.discard(ws)


async def start_ws_server(
    hub: UiWebSocketHub,
    host: str = "0.0.0.0",
    port: int = 8765,
):
    return await websockets.serve(
        hub.handler,
        host,
        port,
        ping_interval=20,
        ping_timeout=20,
        max_size=2 * 1024 * 1024,
        max_queue=hub.max_queue,
    )
