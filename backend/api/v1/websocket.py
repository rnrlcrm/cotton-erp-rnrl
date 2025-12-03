"""
WebSocket API Router

Provides WebSocket endpoints for real-time communication.
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from backend.app.dependencies import get_redis
from backend.core.auth.dependencies import get_current_user_ws
from backend.core.websocket import (
    ConnectionManager,
    HeartbeatManager,
    ShardedChannelManager,
    WebSocketEvent,
    WebSocketMessage,
)
from backend.core.websocket.sharding import ChannelPatterns
from backend.modules.settings.models.settings_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# Global connection manager (singleton)
_connection_manager: Optional[ConnectionManager] = None
_heartbeat_manager: Optional[HeartbeatManager] = None
_sharded_manager: Optional[ShardedChannelManager] = None


def get_connection_manager(redis=Depends(get_redis)) -> ConnectionManager:
    """Get or create connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager(redis=redis)
    return _connection_manager


def get_heartbeat_manager(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
) -> HeartbeatManager:
    """Get or create heartbeat manager"""
    global _heartbeat_manager
    if _heartbeat_manager is None:
        _heartbeat_manager = HeartbeatManager(connection_manager)
    return _heartbeat_manager


def get_sharded_manager(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    redis=Depends(get_redis),
) -> ShardedChannelManager:
    """Get or create sharded channel manager"""
    global _sharded_manager
    if _sharded_manager is None:
        import os
        instance_id = os.getenv("INSTANCE_ID", "default")
        _sharded_manager = ShardedChannelManager(
            connection_manager,
            redis,
            instance_id=instance_id,
        )
    return _sharded_manager


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    heartbeat_manager: HeartbeatManager = Depends(get_heartbeat_manager),
):
    """
    Main WebSocket connection endpoint.
    
    Usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/connect?token=JWT_TOKEN');
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);
        
        // Handle heartbeat
        if (message.event === 'heartbeat') {
            ws.send(JSON.stringify({event: 'pong'}));
        }
    };
    
    // Subscribe to channel (supports any commodity)
    ws.send(JSON.stringify({
        event: 'subscribe',
        channel: 'market:wheat:prices'  // Can be: cotton, wheat, gold, rice, oil, etc.
    }));
    ```
    """
    connection_id = None
    
    try:
        # Connect
        connection_id = await connection_manager.connect(websocket, user.id)
        
        # Register for heartbeat
        heartbeat_manager.register_connection(connection_id)
        
        # Auto-subscribe to user's personal channel
        await connection_manager.subscribe(
            connection_id,
            ChannelPatterns.user_channel(user.id),
        )
        
        # Auto-subscribe to notifications channel
        await connection_manager.subscribe(
            connection_id,
            ChannelPatterns.notifications_channel(user.id),
        )
        
        # Message loop
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                event = message_data.get("event")
                
                # Handle pong
                if event == WebSocketEvent.PONG:
                    await heartbeat_manager.handle_pong(connection_id)
                
                # Handle subscribe
                elif event == WebSocketEvent.SUBSCRIBE:
                    channel = message_data.get("channel")
                    if channel:
                        await connection_manager.subscribe(connection_id, channel)
                
                # Handle unsubscribe
                elif event == WebSocketEvent.UNSUBSCRIBE:
                    channel = message_data.get("channel")
                    if channel:
                        await connection_manager.unsubscribe(connection_id, channel)
                
                # Handle message (send to channel)
                elif event == WebSocketEvent.MESSAGE:
                    channel = message_data.get("channel")
                    if channel:
                        # Broadcast to channel
                        msg = WebSocketMessage(
                            event=WebSocketEvent.MESSAGE,
                            channel=channel,
                            data=message_data.get("data", {}),
                            user_id=user.id,
                        )
                        await connection_manager.broadcast_to_channel(channel, msg)
                
                else:
                    logger.warning(f"Unknown event: {event}")
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from connection {connection_id}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # Cleanup
        if connection_id:
            heartbeat_manager.unregister_connection(connection_id)
            await connection_manager.disconnect(connection_id)


@router.get("/stats")
async def get_websocket_stats(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    heartbeat_manager: HeartbeatManager = Depends(get_heartbeat_manager),
    sharded_manager: ShardedChannelManager = Depends(get_sharded_manager),
):
    """
    Get WebSocket statistics.
    
    Returns connection counts, channels, heartbeat stats, shard distribution.
    """
    return {
        "connections": connection_manager.get_stats(),
        "heartbeat": heartbeat_manager.get_stats(),
        "sharding": await sharded_manager.get_shard_stats(),
    }


@router.get("/channels")
async def list_channels(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    List all active channels.
    
    Returns channel names and subscriber counts.
    """
    return {
        "channels": [
            {
                "name": channel,
                "subscribers": len(users),
            }
            for channel, users in connection_manager.channel_subscriptions.items()
        ],
        "total_channels": len(connection_manager.channel_subscriptions),
    }


@router.post("/broadcast/{channel}")
async def broadcast_to_channel(
    channel: str,
    message: dict,
    user: User = Depends(get_current_user_ws),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Broadcast message to channel (HTTP endpoint for server-side broadcasting).
    
    Use case: Server-triggered events (e.g., price update from background job)
    """
    msg = WebSocketMessage(
        event=WebSocketEvent.BROADCAST,
        channel=channel,
        data=message,
        user_id=user.id,
    )
    
    await connection_manager.broadcast_to_channel(channel, msg)
    
    return {"status": "sent", "channel": channel}


@router.post("/notify/{user_id}")
async def send_notification(
    user_id: UUID,
    message: dict,
    current_user: User = Depends(get_current_user_ws),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Send notification to specific user.
    
    Use case: Admin sends notification to user
    """
    # TODO: Add permission check
    
    msg = WebSocketMessage(
        event=WebSocketEvent.NOTIFICATION,
        data=message,
        user_id=current_user.id,
    )
    
    await connection_manager.send_personal_message(msg, user_id)
    
    return {"status": "sent", "user_id": str(user_id)}
