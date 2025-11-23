"""
Device Fingerprinting & Detection

Generates unique device fingerprints for session tracking across devices.
Detects suspicious logins and new devices.

Security Features:
- Device fingerprinting (browser, OS, IP)
- Suspicious login detection
- New device alerts
- Device trust scoring
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional
from user_agents import parse as parse_user_agent


class DeviceFingerprint:
    """
    Generate device fingerprints for session tracking.
    
    A device fingerprint is a hash of:
    - User-Agent (browser + OS + device)
    - IP address (optional - can change with VPN/mobile networks)
    - Device type (mobile, desktop, tablet)
    """
    
    @staticmethod
    def generate(
        user_agent: str,
        ip_address: Optional[str] = None,
        include_ip: bool = False
    ) -> str:
        """
        Generate device fingerprint hash.
        
        Args:
            user_agent: HTTP User-Agent header
            ip_address: Client IP address
            include_ip: Include IP in fingerprint (less flexible)
        
        Returns:
            SHA256 hash of device fingerprint
        """
        fingerprint_data = {
            'user_agent': user_agent,
        }
        
        if include_ip and ip_address:
            fingerprint_data['ip'] = ip_address
        
        # Create deterministic JSON string
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        
        # Generate SHA256 hash
        return hashlib.sha256(fingerprint_json.encode('utf-8')).hexdigest()
    
    @staticmethod
    def parse_device_info(user_agent: str) -> dict:
        """
        Parse User-Agent to extract device information.
        
        Args:
            user_agent: HTTP User-Agent header
        
        Returns:
            {
                'device_type': 'mobile' | 'desktop' | 'tablet' | 'bot',
                'device_name': 'iPhone', 'Samsung Galaxy', 'Desktop', etc.
                'os_name': 'iOS', 'Android', 'Windows', 'macOS', 'Linux',
                'os_version': '15.0', '11', '10', etc.
                'browser_name': 'Chrome', 'Safari', 'Firefox', 'Edge',
                'browser_version': '96.0', '15.0', etc.
                'is_mobile': bool,
                'is_tablet': bool,
                'is_pc': bool,
                'is_bot': bool,
            }
        """
        ua = parse_user_agent(user_agent)
        
        # Determine device type
        if ua.is_mobile:
            device_type = 'mobile'
        elif ua.is_tablet:
            device_type = 'tablet'
        elif ua.is_bot:
            device_type = 'bot'
        else:
            device_type = 'desktop'
        
        # Generate friendly device name
        device_name = DeviceFingerprint._generate_device_name(ua)
        
        return {
            'device_type': device_type,
            'device_name': device_name,
            'os_name': ua.os.family,
            'os_version': ua.os.version_string,
            'browser_name': ua.browser.family,
            'browser_version': ua.browser.version_string,
            'is_mobile': ua.is_mobile,
            'is_tablet': ua.is_tablet,
            'is_pc': ua.is_pc,
            'is_bot': ua.is_bot,
        }
    
    @staticmethod
    def _generate_device_name(ua) -> str:
        """
        Generate friendly device name.
        
        Examples:
        - "iPhone 13 (iOS 15.0)"
        - "Samsung Galaxy (Android 11)"
        - "Chrome on Windows"
        - "Safari on macOS"
        """
        if ua.is_mobile or ua.is_tablet:
            # Mobile/Tablet: "Device (OS version)"
            device = ua.device.family if ua.device.family != 'Other' else 'Mobile Device'
            os_info = f"{ua.os.family} {ua.os.version_string}" if ua.os.version_string else ua.os.family
            return f"{device} ({os_info})"
        else:
            # Desktop: "Browser on OS"
            browser = ua.browser.family
            os_name = ua.os.family
            return f"{browser} on {os_name}"
    
    @staticmethod
    def is_suspicious_login(
        user_id: str,
        device_fingerprint: str,
        ip_address: str,
        known_devices: list[dict],
        known_ips: list[str]
    ) -> tuple[bool, str]:
        """
        Detect suspicious login attempts.
        
        Suspicious indicators:
        - New device (never seen before)
        - New IP from new location
        - Device type change (mobile → desktop)
        - Rapid location changes
        
        Args:
            user_id: User's ID
            device_fingerprint: Current device fingerprint
            ip_address: Current IP address
            known_devices: List of user's known devices
            known_ips: List of user's known IP addresses
        
        Returns:
            (is_suspicious: bool, reason: str)
        """
        # Check if device is known
        is_known_device = any(
            d.get('device_fingerprint') == device_fingerprint
            for d in known_devices
        )
        
        # Check if IP is known
        is_known_ip = ip_address in known_ips
        
        # Suspicious: New device + New IP
        if not is_known_device and not is_known_ip:
            return (True, "New device from unknown location")
        
        # Suspicious: New device (but known IP is okay)
        if not is_known_device:
            return (True, "New device detected")
        
        return (False, "")
    
    @staticmethod
    def calculate_device_trust_score(
        device_age_days: int,
        total_logins: int,
        failed_logins_last_24h: int,
        is_verified: bool
    ) -> float:
        """
        Calculate device trust score (0.0 to 1.0).
        
        Higher score = more trusted device.
        
        Factors:
        - Device age (older = more trusted)
        - Login frequency (more = more trusted)
        - Failed logins (more = less trusted)
        - Email/SMS verification (verified = more trusted)
        
        Args:
            device_age_days: Days since first login
            total_logins: Total successful logins from this device
            failed_logins_last_24h: Failed login attempts in last 24 hours
            is_verified: Device verified via email/SMS
        
        Returns:
            Trust score (0.0 to 1.0)
        """
        score = 0.0
        
        # Device age (max 0.3)
        if device_age_days > 90:
            score += 0.3
        elif device_age_days > 30:
            score += 0.2
        elif device_age_days > 7:
            score += 0.1
        
        # Login frequency (max 0.3)
        if total_logins > 100:
            score += 0.3
        elif total_logins > 50:
            score += 0.2
        elif total_logins > 10:
            score += 0.1
        
        # Failed logins (subtract up to 0.3)
        if failed_logins_last_24h > 5:
            score -= 0.3
        elif failed_logins_last_24h > 2:
            score -= 0.2
        elif failed_logins_last_24h > 0:
            score -= 0.1
        
        # Verification (0.4)
        if is_verified:
            score += 0.4
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))
