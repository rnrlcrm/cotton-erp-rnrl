"""
WebSocket Connection Manager

Manages WebSocket connections with:
- Connection lifecycle (connect, disconnect)
- Message broadcasting
- Channel subscriptions
- Redis pub/sub for horizontal scaling
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class WebSocketEvent(str, Enum):
    """WebSocket event types"""
    
    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    
    # Subscription events
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Data events
    MESSAGE = "message"
    BROADCAST = "broadcast"
    
    # System events
    HEARTBEAT = "heartbeat"
    PONG = "pong"
    ERROR = "error"
    
    # Domain events
    TRADE_UPDATE = "trade.update"
    PRICE_UPDATE = "price.update"
    ORDER_UPDATE = "order.update"
    NOTIFICATION = "notification"
    USER_TYPING = "user.typing"


class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    event: WebSocketEvent
    channel: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[UUID] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ConnectionManager:
    """
    Manages WebSocket connections.
    
    Features:
    - Connection tracking
    - Channel subscriptions
    - Message broadcasting
    - Redis pub/sub for scaling
    """
    
    def __init__(self, redis: Optional[Redis] = None):
        # Active connections: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[UUID, Dict[str, WebSocket]] = {}
        
        # Channel subscriptions: {channel: {user_id}}
        self.channel_subscriptions: Dict[str, Set[UUID]] = {}
        
        # Connection metadata: {connection_id: {user_id, channels, connected_at}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Redis for pub/sub (optional, for multi-instance scaling)
        self.redis = redis
        self._pubsub_task: Optional[asyncio.Task] = None
        
        # Stats
        self.total_connections = 0
        self.total_messages_sent = 0
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID,
        connection_id: Optional[str] = None,
    ) -> str:
        """
        Accept new WebSocket connection.
        
        Args:
            websocket: WebSocket instance
            user_id: User ID
            connection_id: Optional connection ID
            
        Returns:
            Connection ID
        """
        await websocket.accept()
        
        connection_id = connection_id or str(uuid4())
        
        # Track connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "channels": set(),
            "connected_at": datetime.now(timezone.utc),
        }
        
        self.total_connections += 1
        
        logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}")
        
        # Send welcome message
        await self.send_personal_message(
            message=WebSocketMessage(
                event=WebSocketEvent.CONNECT,
                data={
                    "connection_id": connection_id,
                    "message": "Connected successfully",
                },
                user_id=user_id,
            ),
            user_id=user_id,
            connection_id=connection_id,
        )
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect WebSocket.
        
        Args:
            connection_id: Connection ID
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        user_id = metadata["user_id"]
        
        # Unsubscribe from all channels
        for channel in metadata["channels"]:
            await self.unsubscribe(connection_id, channel)
        
        # Remove connection
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]
            
            # Clean up if no more connections for this user
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove metadata
        del self.connection_metadata[connection_id]
        
        logger.info(f"WebSocket disconnected: connection={connection_id}")
    
    async def subscribe(self, connection_id: str, channel: str):
        """
        Subscribe connection to channel.
        
        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        user_id = metadata["user_id"]
        
        # Add to channel
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        
        self.channel_subscriptions[channel].add(user_id)
        metadata["channels"].add(channel)
        
        logger.info(f"Subscribed: connection={connection_id}, channel={channel}")
        
        # Send confirmation
        await self.send_personal_message(
            message=WebSocketMessage(
                event=WebSocketEvent.SUBSCRIBE,
                channel=channel,
                data={"message": f"Subscribed to {channel}"},
                user_id=user_id,
            ),
            user_id=user_id,
            connection_id=connection_id,
        )
    
    async def unsubscribe(self, connection_id: str, channel: str):
        """
        Unsubscribe connection from channel.
        
        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        user_id = metadata["user_id"]
        
        # Remove from channel
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(user_id)
            
            # Clean up empty channels
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]
        
        metadata["channels"].discard(channel)
        
        logger.info(f"Unsubscribed: connection={connection_id}, channel={channel}")
    
    async def send_personal_message(
        self,
        message: WebSocketMessage,
        user_id: UUID,
        connection_id: Optional[str] = None,
    ):
        """
        Send message to specific user/connection.
        
        Args:
            message: Message to send
            user_id: User ID
            connection_id: Optional specific connection (sends to all if None)
        """
        if user_id not in self.active_connections:
            return
        
        connections = self.active_connections[user_id]
        
        if connection_id:
            # Send to specific connection
            if connection_id in connections:
                await self._send_message(connections[connection_id], message)
        else:
            # Send to all user's connections
            for ws in connections.values():
                await self._send_message(ws, message)
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message: WebSocketMessage,
        exclude_user: Optional[UUID] = None,
    ):
        """
        Broadcast message to all users in channel.
        
        Args:
            channel: Channel name
            message: Message to send
            exclude_user: Optional user to exclude from broadcast
        """
        if channel not in self.channel_subscriptions:
            return
        
        message.channel = channel
        
        for user_id in self.channel_subscriptions[channel]:
            if exclude_user and user_id == exclude_user:
                continue
            
            await self.send_personal_message(message, user_id)
        
        # Publish to Redis for other instances
        if self.redis:
            await self.redis.publish(
                f"websocket:channel:{channel}",
                message.model_dump_json(),
            )
    
    async def broadcast_to_all(
        self,
        message: WebSocketMessage,
        exclude_user: Optional[UUID] = None,
    ):
        """
        Broadcast message to all connected users.
        
        Args:
            message: Message to send
            exclude_user: Optional user to exclude
        """
        for user_id in self.active_connections.keys():
            if exclude_user and user_id == exclude_user:
                continue
            
            await self.send_personal_message(message, user_id)
    
    async def _send_message(self, websocket: WebSocket, message: WebSocketMessage):
        """
        Send message through WebSocket.
        
        Args:
            websocket: WebSocket instance
            message: Message to send
        """
        try:
            await websocket.send_text(message.model_dump_json())
            self.total_messages_sent += 1
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_users = len(self.active_connections)
        total_connections_count = sum(
            len(conns) for conns in self.active_connections.values()
        )
        
        return {
            "total_users_connected": total_users,
            "total_connections": total_connections_count,
            "total_channels": len(self.channel_subscriptions),
            "total_messages_sent": self.total_messages_sent,
            "channels": {
                channel: len(users)
                for channel, users in self.channel_subscriptions.items()
            },
        }
    
    async def start_redis_listener(self):
        """Start listening to Redis pub/sub for cross-instance messages"""
        if not self.redis:
            return
        
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("websocket:channel:*")
        
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                try:
                    # Parse channel from pattern
                    channel = message["channel"].decode().split(":")[-1]
                    
                    # Parse message
                    ws_message = WebSocketMessage.model_validate_json(message["data"])
                    
                    # Broadcast locally (this instance only)
                    if channel in self.channel_subscriptions:
                        for user_id in self.channel_subscriptions[channel]:
                            await self.send_personal_message(ws_message, user_id)
                
                except Exception as e:
                    logger.error(f"Redis message error: {e}")
