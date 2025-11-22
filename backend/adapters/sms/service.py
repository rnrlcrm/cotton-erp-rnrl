"""
SMS Service

Placeholder SMS service for sending notifications.
"""


class SMSService:
    """SMS service for sending text messages"""
    
    def __init__(self):
        """Initialize SMS service"""
        pass
    
    async def send_sms(self, to: str, message: str) -> bool:
        """
        Send SMS
        
        Args:
            to: Recipient phone number
            message: Message text
            
        Returns:
            True if SMS sent successfully
        """
        # TODO: Implement actual SMS sending
        print(f"[SMS] To: {to}, Message: {message}")
        return True
    
    async def send_otp(self, to: str, otp: str) -> bool:
        """
        Send OTP via SMS
        
        Args:
            to: Recipient phone number
            otp: OTP code
            
        Returns:
            True if OTP sent successfully
        """
        message = f"Your OTP is: {otp}. Valid for 5 minutes."
        return await self.send_sms(to, message)
