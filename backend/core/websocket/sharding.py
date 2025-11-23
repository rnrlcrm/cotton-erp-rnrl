"""
Sharded WebSocket Channels

Implements channel sharding for horizontal scalability:
- Consistent hashing for channel assignment
- Redis-backed channel routing
- Load balancing across shards
"""

from __future__ import annotations

import hashlib
import logging
from typing import Dict, List, Optional, Set
from uuid import UUID

from redis.asyncio import Redis

from backend.core.websocket.manager import ConnectionManager, WebSocketMessage

logger = logging.getLogger(__name__)


class ShardedChannelManager:
    """
    Manages WebSocket channels with sharding.
    
    Features:
    - Consistent hashing for shard assignment
    - Dynamic shard rebalancing
    - Cross-shard message routing
    - Redis-backed coordination
    
    Channels are sharded by:
    - User ID (e.g., "user:{user_id}")
    - Organization ID (e.g., "org:{org_id}")
    - Trade ID (e.g., "trade:{trade_id}")
    - Custom channels (e.g., "market:cotton:prices")
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        redis: Redis,
        num_shards: int = 16,
        instance_id: str = "default",
    ):
        self.connection_manager = connection_manager
        self.redis = redis
        self.num_shards = num_shards
        self.instance_id = instance_id
        
        # Shard ownership: {shard_id: instance_id}
        self.shard_owners: Dict[int, str] = {}
        
        # Local channels: {channel: shard_id}
        self.channel_shards: Dict[str, int] = {}
    
    def _get_shard_id(self, channel: str) -> int:
        """
        Calculate shard ID for channel using consistent hashing.
        
        Args:
            channel: Channel name
            
        Returns:
            Shard ID (0 to num_shards-1)
        """
        hash_value = int(hashlib.md5(channel.encode()).hexdigest(), 16)
        return hash_value % self.num_shards
    
    async def claim_shard(self, shard_id: int) -> bool:
        """
        Claim ownership of a shard.
        
        Args:
            shard_id: Shard ID
            
        Returns:
            True if claimed successfully
        """
        # Try to claim shard in Redis (with TTL for failover)
        key = f"websocket:shard:{shard_id}:owner"
        
        # Set with NX (only if not exists) and EX (expiry in 30 seconds)
        claimed = await self.redis.set(
            key,
            self.instance_id,
            nx=True,
            ex=30,
        )
        
        if claimed:
            self.shard_owners[shard_id] = self.instance_id
            logger.info(f"Claimed shard {shard_id} for instance {self.instance_id}")
            return True
        
        return False
    
    async def renew_shard_ownership(self, shard_id: int):
        """
        Renew shard ownership (heartbeat).
        
        Args:
            shard_id: Shard ID
        """
        key = f"websocket:shard:{shard_id}:owner"
        
        # Only renew if we own it
        current_owner = await self.redis.get(key)
        if current_owner and current_owner.decode() == self.instance_id:
            await self.redis.expire(key, 30)
    
    async def get_shard_owner(self, shard_id: int) -> Optional[str]:
        """
        Get current owner of shard.
        
        Args:
            shard_id: Shard ID
            
        Returns:
            Instance ID or None
        """
        key = f"websocket:shard:{shard_id}:owner"
        owner = await self.redis.get(key)
        return owner.decode() if owner else None
    
    async def subscribe_to_channel(self, connection_id: str, channel: str):
        """
        Subscribe connection to sharded channel.
        
        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        shard_id = self._get_shard_id(channel)
        
        # Check if we own this shard
        owner = await self.get_shard_owner(shard_id)
        
        if owner != self.instance_id:
            # Try to claim it
            claimed = await self.claim_shard(shard_id)
            if not claimed:
                logger.warning(
                    f"Cannot subscribe to {channel}: shard {shard_id} owned by {owner}"
                )
                return
        
        # Subscribe locally
        await self.connection_manager.subscribe(connection_id, channel)
        self.channel_shards[channel] = shard_id
        
        # Register channel in Redis for cross-instance routing
        await self.redis.sadd(f"websocket:shard:{shard_id}:channels", channel)
    
    async def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """
        Unsubscribe connection from sharded channel.
        
        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        await self.connection_manager.unsubscribe(connection_id, channel)
        
        # Check if channel is empty
        if channel not in self.connection_manager.channel_subscriptions:
            shard_id = self.channel_shards.pop(channel, None)
            if shard_id is not None:
                # Remove from Redis
                await self.redis.srem(
                    f"websocket:shard:{shard_id}:channels",
                    channel,
                )
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message: WebSocketMessage,
        exclude_user: Optional[UUID] = None,
    ):
        """
        Broadcast message to sharded channel.
        
        If channel is on another instance, routes via Redis.
        
        Args:
            channel: Channel name
            message: Message to send
            exclude_user: Optional user to exclude
        """
        shard_id = self._get_shard_id(channel)
        owner = await self.get_shard_owner(shard_id)
        
        if owner == self.instance_id:
            # We own this shard, broadcast locally
            await self.connection_manager.broadcast_to_channel(
                channel,
                message,
                exclude_user,
            )
        else:
            # Route to correct instance via Redis
            await self.redis.publish(
                f"websocket:shard:{shard_id}:channel:{channel}",
                message.model_dump_json(),
            )
    
    async def get_shard_stats(self) -> Dict[str, any]:
        """Get statistics about shards"""
        stats = {
            "instance_id": self.instance_id,
            "num_shards": self.num_shards,
            "owned_shards": len(self.shard_owners),
            "local_channels": len(self.channel_shards),
            "shard_distribution": {},
        }
        
        # Count channels per shard
        shard_counts: Dict[int, int] = {}
        for shard_id in self.channel_shards.values():
            shard_counts[shard_id] = shard_counts.get(shard_id, 0) + 1
        
        stats["shard_distribution"] = shard_counts
        
        return stats
    
    async def rebalance_shards(self):
        """
        Rebalance shards across instances.
        
        Called periodically to redistribute load.
        """
        # Get all instances
        instances = set()
        for shard_id in range(self.num_shards):
            owner = await self.get_shard_owner(shard_id)
            if owner:
                instances.add(owner)
        
        if not instances:
            return
        
        # Calculate target shards per instance
        target_per_instance = self.num_shards / len(instances)
        
        # Count our shards
        our_shards = sum(1 for owner in self.shard_owners.values() if owner == self.instance_id)
        
        # If we have too many, release some
        if our_shards > target_per_instance * 1.2:  # 20% tolerance
            excess = int(our_shards - target_per_instance)
            shards_to_release = list(self.shard_owners.keys())[:excess]
            
            for shard_id in shards_to_release:
                # Delete ownership key (let other instances claim)
                await self.redis.delete(f"websocket:shard:{shard_id}:owner")
                del self.shard_owners[shard_id]
                logger.info(f"Released shard {shard_id} for rebalancing")
        
        # If we have too few, try to claim more
        elif our_shards < target_per_instance * 0.8:  # 20% tolerance
            needed = int(target_per_instance - our_shards)
            
            for shard_id in range(self.num_shards):
                if needed <= 0:
                    break
                
                if shard_id not in self.shard_owners:
                    if await self.claim_shard(shard_id):
                        needed -= 1


# Predefined channel patterns
class ChannelPatterns:
    """Common channel patterns for the ERP system"""
    
    @staticmethod
    def user_channel(user_id: UUID) -> str:
        """Personal user channel"""
        return f"user:{user_id}"
    
    @staticmethod
    def org_channel(org_id: UUID) -> str:
        """Organization-wide channel"""
        return f"org:{org_id}"
    
    @staticmethod
    def trade_channel(trade_id: UUID) -> str:
        """Trade-specific channel"""
        return f"trade:{trade_id}"
    
    @staticmethod
    def contract_channel(contract_id: UUID) -> str:
        """Contract-specific channel"""
        return f"contract:{contract_id}"
    
    @staticmethod
    def market_prices_channel(commodity: str) -> str:
        """Market prices for commodity"""
        return f"market:{commodity}:prices"
    
    @staticmethod
    def notifications_channel(user_id: UUID) -> str:
        """User notifications channel"""
        return f"notifications:{user_id}"
    
    @staticmethod
    def chat_channel(chat_id: UUID) -> str:
        """Chat room channel"""
        return f"chat:{chat_id}"
