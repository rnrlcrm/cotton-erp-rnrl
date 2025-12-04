"""
WebSocket Negotiation Room Manager - Real-Time Communication

Manages WebSocket connections for live negotiation rooms.
Broadcasts events to all participants in real-time.

Events:
- offer.created - New offer/counter-offer
- offer.accepted - Offer accepted
- offer.rejected - Offer rejected  
- message.received - New chat message
- negotiation.status_changed - Status update
- typing.indicator - User is typing
"""

from typing import Dict, Set, Optional
from uuid import UUID
import json
import asyncio

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis


class NegotiationRoomManager:
    """
    Manages WebSocket connections for negotiation rooms.
    
    Architecture:
    - One room per negotiation
    - Multiple connections per room (buyer, seller, admins)
    - Redis pub/sub for multi-instance scalability
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        # Active WebSocket connections: {negotiation_id: {websocket1, websocket2}}
        self.active_rooms: Dict[UUID, Set[WebSocket]] = {}
        
        # WebSocket to user mapping: {websocket: user_partner_id}
        self.websocket_users: Dict[WebSocket, UUID] = {}
        
        # Redis for multi-instance coordination
        self.redis = redis_client
    
    async def connect(
        self,
        negotiation_id: UUID,
        websocket: WebSocket,
        user_partner_id: UUID
    ):
        """
        Connect user to negotiation room.
        
        Args:
            negotiation_id: Negotiation UUID
            websocket: WebSocket connection
            user_partner_id: User's partner ID
        """
        await websocket.accept()
        
        # Add to room
        if negotiation_id not in self.active_rooms:
            self.active_rooms[negotiation_id] = set()
        
        self.active_rooms[negotiation_id].add(websocket)
        self.websocket_users[websocket] = user_partner_id
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection.established",
            "negotiation_id": str(negotiation_id),
            "user_id": str(user_partner_id),
            "timestamp": "now"
        })
        
        # Subscribe to Redis channel if available
        if self.redis:
            # TODO: Implement Redis pub/sub for multi-instance
            pass
    
    async def disconnect(
        self,
        negotiation_id: UUID,
        websocket: WebSocket
    ):
        """
        Disconnect user from negotiation room.
        
        Args:
            negotiation_id: Negotiation UUID
            websocket: WebSocket connection
        """
        if negotiation_id in self.active_rooms:
            self.active_rooms[negotiation_id].discard(websocket)
            
            # Remove empty rooms
            if not self.active_rooms[negotiation_id]:
                del self.active_rooms[negotiation_id]
        
        if websocket in self.websocket_users:
            del self.websocket_users[websocket]
    
    async def broadcast_offer(
        self,
        negotiation_id: UUID,
        offer_data: dict,
        exclude_sender: bool = False,
        sender_id: Optional[UUID] = None
    ):
        """
        Broadcast new offer to all participants.
        
        Args:
            negotiation_id: Negotiation UUID
            offer_data: Offer details
            exclude_sender: Don't send to sender
            sender_id: Sender's user ID (for exclusion)
        """
        if negotiation_id not in self.active_rooms:
            return
        
        message = {
            "type": "offer.created",
            "negotiation_id": str(negotiation_id),
            **offer_data
        }
        
        for websocket in self.active_rooms[negotiation_id]:
            # Skip sender if requested
            if exclude_sender and sender_id:
                ws_user_id = self.websocket_users.get(websocket)
                if ws_user_id == sender_id:
                    continue
            
            try:
                await websocket.send_json(message)
            except Exception:
                # Connection broken, will be cleaned up
                pass
    
    async def broadcast_message(
        self,
        negotiation_id: UUID,
        message_data: dict,
        exclude_sender: bool = False,
        sender_id: Optional[UUID] = None
    ):
        """
        Broadcast chat message to all participants.
        
        Args:
            negotiation_id: Negotiation UUID
            message_data: Message details
            exclude_sender: Don't send to sender
            sender_id: Sender's user ID (for exclusion)
        """
        if negotiation_id not in self.active_rooms:
            return
        
        message = {
            "type": "message.received",
            "negotiation_id": str(negotiation_id),
            **message_data
        }
        
        for websocket in self.active_rooms[negotiation_id]:
            if exclude_sender and sender_id:
                ws_user_id = self.websocket_users.get(websocket)
                if ws_user_id == sender_id:
                    continue
            
            try:
                await websocket.send_json(message)
            except Exception:
                pass
    
    async def broadcast_status_change(
        self,
        negotiation_id: UUID,
        new_status: str,
        additional_data: Optional[dict] = None
    ):
        """
        Broadcast status change to all participants.
        
        Args:
            negotiation_id: Negotiation UUID
            new_status: New status (ACCEPTED, REJECTED, EXPIRED)
            additional_data: Extra data to include
        """
        if negotiation_id not in self.active_rooms:
            return
        
        message = {
            "type": "negotiation.status_changed",
            "negotiation_id": str(negotiation_id),
            "new_status": new_status,
            **(additional_data or {})
        }
        
        for websocket in self.active_rooms[negotiation_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                pass
    
    async def broadcast_typing_indicator(
        self,
        negotiation_id: UUID,
        user_id: UUID,
        is_typing: bool
    ):
        """
        Broadcast typing indicator to other party.
        
        Args:
            negotiation_id: Negotiation UUID
            user_id: User who is typing
            is_typing: True if typing, False if stopped
        """
        if negotiation_id not in self.active_rooms:
            return
        
        message = {
            "type": "typing.indicator",
            "negotiation_id": str(negotiation_id),
            "user_id": str(user_id),
            "is_typing": is_typing
        }
        
        for websocket in self.active_rooms[negotiation_id]:
            # Don't send typing indicator to self
            ws_user_id = self.websocket_users.get(websocket)
            if ws_user_id == user_id:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception:
                pass
    
    async def send_to_user(
        self,
        negotiation_id: UUID,
        user_id: UUID,
        message: dict
    ):
        """
        Send message to specific user in room.
        
        Args:
            negotiation_id: Negotiation UUID
            user_id: Target user ID
            message: Message to send
        """
        if negotiation_id not in self.active_rooms:
            return
        
        for websocket in self.active_rooms[negotiation_id]:
            ws_user_id = self.websocket_users.get(websocket)
            if ws_user_id == user_id:
                try:
                    await websocket.send_json(message)
                except Exception:
                    pass
                break
    
    def get_active_users(self, negotiation_id: UUID) -> Set[UUID]:
        """
        Get list of users currently connected to room.
        
        Args:
            negotiation_id: Negotiation UUID
        
        Returns:
            Set of user IDs
        """
        if negotiation_id not in self.active_rooms:
            return set()
        
        users = set()
        for websocket in self.active_rooms[negotiation_id]:
            user_id = self.websocket_users.get(websocket)
            if user_id:
                users.add(user_id)
        
        return users
    
    def is_user_online(self, negotiation_id: UUID, user_id: UUID) -> bool:
        """
        Check if user is currently connected to room.
        
        Args:
            negotiation_id: Negotiation UUID
            user_id: User ID to check
        
        Returns:
            True if user is online
        """
        active_users = self.get_active_users(negotiation_id)
        return user_id in active_users


# Global instance
negotiation_room_manager = NegotiationRoomManager()
