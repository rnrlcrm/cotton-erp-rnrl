"""
OTP Service for Mobile Authentication

Handles OTP generation, storage in Redis, and verification
SMS integration placeholder - to be implemented with provider
"""

import random
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.outbox import OutboxRepository


class OTPService:
    """Handle OTP generation, storage, and verification"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.outbox_repo = OutboxRepository(db)
        self.otp_ttl = 300  # 5 minutes
        self.max_attempts = 3
        self.rate_limit_window = 60  # 1 minute between OTP requests
        
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    async def can_send_otp(self, mobile_number: str) -> bool:
        """
        Check if OTP can be sent (rate limiting)
        
        Returns:
            True if OTP can be sent, False if rate limited
        """
        rate_limit_key = f"otp_rate_limit:{mobile_number}"
        last_sent = await self.redis.get(rate_limit_key)
        
        if last_sent:
            return False
        
        return True
    
    async def send_otp(self, mobile_number: str) -> dict:
        """
        Generate OTP and store in Redis
        
        Args:
            mobile_number: User's mobile number
        
        Returns:
            {
                "otp": "123456",  # Only in development mode
                "expires_at": datetime,
                "sent_via": "sms"
            }
        
        Raises:
            HTTPException: If rate limited
        """
        # Check rate limiting
        if not await self.can_send_otp(mobile_number):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait 60 seconds before requesting another OTP"
            )
        
        # Generate OTP
        otp = self.generate_otp()
        
        # Store in Redis with TTL
        otp_key = f"otp:{mobile_number}"
        attempts_key = f"otp_attempts:{mobile_number}"
        rate_limit_key = f"otp_rate_limit:{mobile_number}"
        
        # Store OTP
        await self.redis.setex(otp_key, self.otp_ttl, otp)
        
        # Reset attempts counter
        await self.redis.setex(attempts_key, self.otp_ttl, "0")
        
        # Set rate limit
        await self.redis.setex(rate_limit_key, self.rate_limit_window, "1")
        
        # Send SMS (placeholder - to be implemented)
        await self._send_sms(mobile_number, otp)
        
        return {
            "otp": otp,  # TODO: Remove this in production
            "expires_at": datetime.utcnow() + timedelta(seconds=self.otp_ttl),
            "sent_via": "sms"
        }
    
    async def verify_otp(self, mobile_number: str, otp: str) -> bool:
        """
        Verify OTP from Redis
        
        Args:
            mobile_number: User's mobile number
            otp: OTP to verify
        
        Returns:
            True if OTP is valid
        
        Raises:
            HTTPException: If too many attempts or OTP expired
        """
        otp_key = f"otp:{mobile_number}"
        attempts_key = f"otp_attempts:{mobile_number}"
        
        # Check attempts
        attempts = await self.redis.get(attempts_key)
        if attempts and int(attempts) >= self.max_attempts:
            # Delete OTP to prevent further attempts
            await self.redis.delete(otp_key)
            await self.redis.delete(attempts_key)
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP verification attempts. Please request a new OTP."
            )
        
        # Get stored OTP
        stored_otp = await self.redis.get(otp_key)
        
        if not stored_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not found. Please request a new OTP."
            )
        
        # Increment attempts
        if attempts:
            await self.redis.incr(attempts_key)
        else:
            await self.redis.setex(attempts_key, self.otp_ttl, "1")
        
        # Verify OTP
        if stored_otp.decode() != otp:
            remaining_attempts = self.max_attempts - int(await self.redis.get(attempts_key))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
            )
        
        # OTP verified - delete from Redis
        await self.redis.delete(otp_key)
        await self.redis.delete(attempts_key)
        
        return True
    
    async def _send_sms(self, mobile_number: str, otp: str):
        """
        Send SMS via provider
        
        TODO: Integrate with actual SMS provider (Twilio/MSG91/AWS SNS)
        
        For now, just log to console (development mode)
        """
        print(f"\n{'='*60}")
        print(f"📱 SMS to {mobile_number}")
        print(f"{'='*60}")
        print(f"Your Commodity ERP verification code is: {otp}")
        print(f"Valid for 5 minutes. Do not share this code.")
        print(f"{'='*60}\n")
        
        # TODO: Production implementation
        """
        # Example with Twilio:
        from twilio.rest import Client
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your Commodity ERP verification code is: {otp}. Valid for 5 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=mobile_number
        )
        
        # Example with MSG91 (India):
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.msg91.com/api/v5/otp',
                json={
                    'template_id': settings.MSG91_TEMPLATE_ID,
                    'mobile': mobile_number,
                    'otp': otp
                },
                headers={'authkey': settings.MSG91_AUTH_KEY}
            )
        
        # Example with AWS SNS:
        import boto3
        
        sns = boto3.client('sns', region_name=settings.AWS_REGION)
        sns.publish(
            PhoneNumber=mobile_number,
            Message=f"Your Commodity ERP verification code is: {otp}. Valid for 5 minutes."
        )
        """
