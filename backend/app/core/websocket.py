# app/core/websocket.py
"""
ConnectionManager — Gestión de conexiones WebSocket en memoria.

Rooms por rol (staff):
  "role:PEDIDOS" — usuarios con rol PEDIDOS
  "role:ADMIN"   — usuarios con rol ADMIN
  "role:CLIENT"  — usuarios con rol CLIENT (recibe updates de sus propios pedidos)

Rooms por pedido (suscripción individual):
  "order:{id}"   — socket(s) suscritos a ese pedido específico

STOCK no participa en WebSocket (no interviene en el flujo de pedidos en tiempo real).

Toda la estructura vive en memoria del proceso uvicorn.
Para escalar horizontalmente reemplazar por Redis Pub/Sub.
"""
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """
    Singleton que gestiona las conexiones WebSocket activas.

    Estructura interna:
      _rooms:        dict[str, set[WebSocket]]  — room_id → sockets en esa room
      _socket_rooms: dict[WebSocket, set[str]]  — socket → rooms donde está (inverso para limpiar)
    """

    def __init__(self) -> None:
        # room_id → conjunto de sockets (ej. "role:PEDIDOS", "order:42")
        self._rooms: dict[str, set[WebSocket]] = {}
        # socket → conjunto de rooms donde está registrado
        self._socket_rooms: dict[WebSocket, set[str]] = {}

    # ── Conexión / desconexión ────────────────────────────────────────────────

    def connect(self, ws: WebSocket, roles: list[str]) -> None:
        """
        Registra el WebSocket (ya aceptado por el endpoint) y lo une
        a las rooms de rol que le correspondan.
        STOCK se excluye explícitamente; no participa en pedidos en tiempo real.
        """
        self._socket_rooms[ws] = set()
        for role in roles:
            if role in ("ADMIN", "PEDIDOS", "CLIENT"):
                self._join(ws, f"role:{role}")

    def disconnect(self, ws: WebSocket) -> None:
        """Elimina el socket de todas sus rooms y del mapa de sockets."""
        rooms = self._socket_rooms.pop(ws, set())
        for room in rooms:
            room_set = self._rooms.get(room)
            if room_set:
                room_set.discard(ws)
                if not room_set:  # room vacía → limpiar
                    self._rooms.pop(room, None)

    # ── Suscripción a pedido individual ──────────────────────────────────────

    def join_order_room(self, ws: WebSocket, order_id: int) -> None:
        """Suscribe el socket a la room del pedido para notificaciones punto a punto."""
        self._join(ws, f"order:{order_id}")

    def leave_order_room(self, ws: WebSocket, order_id: int) -> None:
        """Desuscribe el socket de la room del pedido."""
        room = f"order:{order_id}"
        room_set = self._rooms.get(room)
        if room_set:
            room_set.discard(ws)
        self._socket_rooms.get(ws, set()).discard(room)

    # ── Broadcasts ───────────────────────────────────────────────────────────

    async def broadcast_to_role(self, role: str, event: str, data: Any) -> None:
        """Envía un evento JSON a todos los sockets en la room `role:{role}`."""
        await self._broadcast_to_room(f"role:{role}", event, data)

    async def broadcast_to_roles(
        self, roles: list[str], event: str, data: Any
    ) -> None:
        """
        Envía un evento JSON a la UNIÓN de las rooms de los roles indicados.
        Deduplica: un socket presente en varias rooms solo recibe un envío.
        """
        seen: set[WebSocket] = set()
        payload = self._encode(event, data)
        for role in roles:
            for ws in list(self._rooms.get(f"role:{role}", set())):
                if ws not in seen:
                    seen.add(ws)
                    await self._safe_send(ws, payload)

    async def broadcast_to_order(
        self, order_id: int, event: str, data: Any
    ) -> None:
        """Envía un evento JSON a los sockets suscritos al pedido específico."""
        await self._broadcast_to_room(f"order:{order_id}", event, data)

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _join(self, ws: WebSocket, room: str) -> None:
        """Añade el socket a la room (en ambos mapas)."""
        self._rooms.setdefault(room, set()).add(ws)
        self._socket_rooms.setdefault(ws, set()).add(room)

    @staticmethod
    def _encode(event: str, data: Any) -> str:
        """Serializa el mensaje como JSON; usa str() como fallback para tipos no serializables."""
        return json.dumps({"event": event, "data": data}, default=str)

    async def _broadcast_to_room(self, room: str, event: str, data: Any) -> None:
        payload = self._encode(event, data)
        for ws in list(self._rooms.get(room, set())):
            await self._safe_send(ws, payload)

    @staticmethod
    async def _safe_send(ws: WebSocket, payload: str) -> None:
        """
        Intenta enviar sin crashear si el socket ya cerró.
        Los sockets rotos se limpian en el próximo WebSocketDisconnect del endpoint.
        """
        try:
            await ws.send_text(payload)
        except Exception:
            pass  # socket ya cerrado — se limpiará en disconnect()


# ── Singleton global ──────────────────────────────────────────────────────────
manager = ConnectionManager()
