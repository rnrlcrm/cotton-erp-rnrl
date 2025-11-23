"""
WebSocket Real-time Infrastructure

Exports:
- ConnectionManager: Main WebSocket connection manager
- ShardedChannelManager: Sharded channels for scalability
- HeartbeatManager: Heartbeat & reconnection logic
- WebSocketMessage: Message schema
- WebSocketEvent: Event types
"""

from backend.core.websocket.manager import ConnectionManager, WebSocketMessage, WebSocketEvent
from backend.core.websocket.sharding import ShardedChannelManager
from backend.core.websocket.heartbeat import HeartbeatManager

__all__ = [
    "ConnectionManager",
    "ShardedChannelManager",
    "HeartbeatManager",
    "WebSocketMessage",
    "WebSocketEvent",
]
