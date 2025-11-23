"""
WebSocket Heartbeat & Reconnection Logic

Features:
- Heartbeat/ping-pong mechanism
- Automatic reconnection detection
- Connection state tracking
- Idle connection cleanup
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import WebSocket

from backend.core.websocket.manager import ConnectionManager, WebSocketEvent, WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionState:
    """Tracks state of a WebSocket connection"""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.last_heartbeat: Optional[datetime] = None
        self.last_pong: Optional[datetime] = None
        self.missed_heartbeats = 0
        self.is_alive = True
        self.connected_at = datetime.now(timezone.utc)


class HeartbeatManager:
    """
    Manages WebSocket heartbeats and reconnection.
    
    Features:
    - Periodic heartbeat/ping
    - Pong response tracking
    - Idle connection detection
    - Automatic cleanup of dead connections
    - Reconnection token generation
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        heartbeat_interval: int = 30,  # seconds
        max_missed_heartbeats: int = 3,
        idle_timeout: int = 300,  # 5 minutes
    ):
        self.connection_manager = connection_manager
        self.heartbeat_interval = heartbeat_interval
        self.max_missed_heartbeats = max_missed_heartbeats
        self.idle_timeout = idle_timeout
        
        # Connection states: {connection_id: ConnectionState}
        self.connection_states: Dict[str, ConnectionState] = {}
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Stats
        self.total_heartbeats_sent = 0
        self.total_pongs_received = 0
        self.total_timeouts = 0
    
    def register_connection(self, connection_id: str):
        """
        Register connection for heartbeat tracking.
        
        Args:
            connection_id: Connection ID
        """
        self.connection_states[connection_id] = ConnectionState(connection_id)
        logger.debug(f"Registered connection for heartbeat: {connection_id}")
    
    def unregister_connection(self, connection_id: str):
        """
        Unregister connection.
        
        Args:
            connection_id: Connection ID
        """
        if connection_id in self.connection_states:
            del self.connection_states[connection_id]
            logger.debug(f"Unregistered connection: {connection_id}")
    
    async def handle_pong(self, connection_id: str):
        """
        Handle pong response from client.
        
        Args:
            connection_id: Connection ID
        """
        if connection_id not in self.connection_states:
            return
        
        state = self.connection_states[connection_id]
        state.last_pong = datetime.now(timezone.utc)
        state.missed_heartbeats = 0
        state.is_alive = True
        
        self.total_pongs_received += 1
        
        logger.debug(f"Received pong from {connection_id}")
    
    async def send_heartbeat(self, connection_id: str):
        """
        Send heartbeat to connection.
        
        Args:
            connection_id: Connection ID
        """
        if connection_id not in self.connection_manager.connection_metadata:
            return
        
        metadata = self.connection_manager.connection_metadata[connection_id]
        user_id = metadata["user_id"]
        
        # Send heartbeat message
        message = WebSocketMessage(
            event=WebSocketEvent.HEARTBEAT,
            data={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "connection_id": connection_id,
            },
            user_id=user_id,
        )
        
        await self.connection_manager.send_personal_message(
            message,
            user_id,
            connection_id,
        )
        
        # Update state
        if connection_id in self.connection_states:
            state = self.connection_states[connection_id]
            state.last_heartbeat = datetime.now(timezone.utc)
            state.missed_heartbeats += 1
        
        self.total_heartbeats_sent += 1
    
    async def heartbeat_loop(self):
        """
        Periodic heartbeat sender.
        
        Runs in background, sends heartbeats to all connections.
        """
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Send heartbeat to all connections
                for connection_id in list(self.connection_states.keys()):
                    await self.send_heartbeat(connection_id)
                
                logger.debug(f"Sent heartbeats to {len(self.connection_states)} connections")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    async def cleanup_loop(self):
        """
        Periodic cleanup of dead/idle connections.
        
        Runs in background, checks for:
        - Missed heartbeats (connection dead)
        - Idle connections (no activity)
        """
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                now = datetime.now(timezone.utc)
                to_cleanup = []
                
                for connection_id, state in self.connection_states.items():
                    # Check missed heartbeats
                    if state.missed_heartbeats >= self.max_missed_heartbeats:
                        logger.warning(
                            f"Connection {connection_id} missed {state.missed_heartbeats} "
                            f"heartbeats, marking as dead"
                        )
                        to_cleanup.append(connection_id)
                        self.total_timeouts += 1
                        continue
                    
                    # Check idle timeout
                    last_activity = state.last_pong or state.connected_at
                    idle_time = (now - last_activity).total_seconds()
                    
                    if idle_time > self.idle_timeout:
                        logger.warning(
                            f"Connection {connection_id} idle for {idle_time}s, disconnecting"
                        )
                        to_cleanup.append(connection_id)
                        self.total_timeouts += 1
                
                # Cleanup dead connections
                for connection_id in to_cleanup:
                    await self.connection_manager.disconnect(connection_id)
                    self.unregister_connection(connection_id)
                
                if to_cleanup:
                    logger.info(f"Cleaned up {len(to_cleanup)} dead/idle connections")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def start(self):
        """Start heartbeat and cleanup background tasks"""
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            logger.info("Started heartbeat loop")
        
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_loop())
            logger.info("Started cleanup loop")
    
    async def stop(self):
        """Stop background tasks"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        logger.info("Stopped heartbeat manager")
    
    def get_stats(self) -> Dict[str, any]:
        """Get heartbeat statistics"""
        alive_connections = sum(
            1 for state in self.connection_states.values() if state.is_alive
        )
        
        return {
            "total_connections": len(self.connection_states),
            "alive_connections": alive_connections,
            "dead_connections": len(self.connection_states) - alive_connections,
            "total_heartbeats_sent": self.total_heartbeats_sent,
            "total_pongs_received": self.total_pongs_received,
            "total_timeouts": self.total_timeouts,
            "heartbeat_interval": self.heartbeat_interval,
            "max_missed_heartbeats": self.max_missed_heartbeats,
            "idle_timeout": self.idle_timeout,
        }
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, any]]:
        """
        Get detailed connection info.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            Connection info or None
        """
        if connection_id not in self.connection_states:
            return None
        
        state = self.connection_states[connection_id]
        now = datetime.now(timezone.utc)
        
        return {
            "connection_id": connection_id,
            "is_alive": state.is_alive,
            "connected_at": state.connected_at.isoformat(),
            "uptime_seconds": (now - state.connected_at).total_seconds(),
            "last_heartbeat": state.last_heartbeat.isoformat() if state.last_heartbeat else None,
            "last_pong": state.last_pong.isoformat() if state.last_pong else None,
            "missed_heartbeats": state.missed_heartbeats,
            "idle_seconds": (now - (state.last_pong or state.connected_at)).total_seconds(),
        }


class ReconnectionManager:
    """
    Manages reconnection tokens for seamless reconnection.
    
    When a client disconnects, they can reconnect using a token
    to restore their previous session (subscriptions, state).
    """
    
    def __init__(self, connection_manager: ConnectionManager, token_ttl: int = 300):
        self.connection_manager = connection_manager
        self.token_ttl = token_ttl  # 5 minutes
        
        # Reconnection tokens: {token: {user_id, channels, expires_at}}
        self.reconnection_tokens: Dict[str, Dict[str, any]] = {}
    
    async def generate_reconnection_token(self, connection_id: str) -> Optional[str]:
        """
        Generate reconnection token for connection.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            Reconnection token or None
        """
        if connection_id not in self.connection_manager.connection_metadata:
            return None
        
        metadata = self.connection_manager.connection_metadata[connection_id]
        
        # Generate token
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Store token
        self.reconnection_tokens[token] = {
            "user_id": metadata["user_id"],
            "channels": list(metadata["channels"]),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.token_ttl),
        }
        
        logger.info(f"Generated reconnection token for connection {connection_id}")
        return token
    
    async def reconnect_with_token(
        self,
        token: str,
        new_connection_id: str,
    ) -> bool:
        """
        Reconnect using token.
        
        Args:
            token: Reconnection token
            new_connection_id: New connection ID
            
        Returns:
            True if reconnected successfully
        """
        if token not in self.reconnection_tokens:
            return False
        
        token_data = self.reconnection_tokens[token]
        
        # Check expiry
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            del self.reconnection_tokens[token]
            return False
        
        # Restore subscriptions
        for channel in token_data["channels"]:
            await self.connection_manager.subscribe(new_connection_id, channel)
        
        # Cleanup token
        del self.reconnection_tokens[token]
        
        logger.info(
            f"Reconnected connection {new_connection_id} with "
            f"{len(token_data['channels'])} channels"
        )
        return True
    
    async def cleanup_expired_tokens(self):
        """Remove expired reconnection tokens"""
        now = datetime.now(timezone.utc)
        expired = [
            token
            for token, data in self.reconnection_tokens.items()
            if now > data["expires_at"]
        ]
        
        for token in expired:
            del self.reconnection_tokens[token]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired reconnection tokens")
