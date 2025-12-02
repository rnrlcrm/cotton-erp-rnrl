"""
Load testing script for Commodity ERP Backend.

Tests system capacity under high concurrent load:
- 1000+ concurrent users
- Multiple endpoint types
- Database connection pool
- Rate limiting behavior
- Response time validation

Usage:
    # Install locust
    pip install locust

    # Run with 1000 users, spawn 100/sec
    locust -f tests/load_test.py --headless -u 1000 -r 100 --run-time 5m --host http://localhost:8000

    # Run with web UI
    locust -f tests/load_test.py --host http://localhost:8000
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from typing import Optional

# Test data
TEST_ORGANIZATIONS = [
    "ORG-001", "ORG-002", "ORG-003", "ORG-004", "ORG-005"
]

TEST_LOCATIONS = [
    "LOC-001", "LOC-002", "LOC-003", "LOC-004", "LOC-005"
]

TEST_COMMODITIES = [
    "cotton", "wheat", "rice", "corn", "soybean"
]


class CottonERPUser(HttpUser):
    """
    Simulates a typical Commodity ERP user performing various operations.
    
    Task distribution:
    - 50%: Read operations (list, get)
    - 30%: Write operations (create, update)
    - 20%: Search/filter operations
    """
    
    # Wait 1-3 seconds between tasks (simulating real user behavior)
    wait_time = between(1, 3)
    
    # Auth token (set during on_start)
    auth_token: Optional[str] = None
    
    def on_start(self):
        """
        Called when a user starts.
        Authenticate and get auth token.
        """
        # Try to login (if auth endpoint exists)
        try:
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "username": f"test_user_{random.randint(1, 1000)}",
                    "password": "test_password_123"
                },
                catch_response=True
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
            else:
                # Use a test token for load testing
                self.auth_token = "test_token_for_load_testing"
        except Exception:
            # Fallback to test token
            self.auth_token = "test_token_for_load_testing"
    
    def _get_headers(self) -> dict:
        """Get headers with auth token."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    # ==================== READ OPERATIONS (50%) ====================
    
    @task(15)
    def list_commodities(self):
        """List commodities (15% of requests)."""
        self.client.get(
            "/api/v1/settings/commodities",
            headers=self._get_headers(),
            name="/api/v1/settings/commodities [LIST]"
        )
    
    @task(15)
    def list_locations(self):
        """List locations (15% of requests)."""
        self.client.get(
            "/api/v1/settings/locations",
            headers=self._get_headers(),
            name="/api/v1/settings/locations [LIST]"
        )
    
    @task(10)
    def list_organizations(self):
        """List organizations (10% of requests)."""
        self.client.get(
            "/api/v1/settings/organizations",
            headers=self._get_headers(),
            name="/api/v1/settings/organizations [LIST]"
        )
    
    @task(5)
    def get_commodity_by_id(self):
        """Get specific commodity (5% of requests)."""
        commodity_name = random.choice(TEST_COMMODITIES)
        self.client.get(
            f"/api/v1/settings/commodities/{commodity_name}",
            headers=self._get_headers(),
            name="/api/v1/settings/commodities/:id [GET]"
        )
    
    @task(5)
    def get_location_by_id(self):
        """Get specific location (5% of requests)."""
        location_code = random.choice(TEST_LOCATIONS)
        self.client.get(
            f"/api/v1/settings/locations/{location_code}",
            headers=self._get_headers(),
            name="/api/v1/settings/locations/:id [GET]"
        )
    
    # ==================== WRITE OPERATIONS (30%) ====================
    
    @task(10)
    def create_commodity(self):
        """Create new commodity (10% of requests)."""
        commodity_data = {
            "name": f"test_commodity_{random.randint(1000, 9999)}",
            "description": "Load test commodity",
            "category": random.choice(["COTTON", "GRAIN", "SEED"]),
            "unit": "KG",
            "hsn_code": f"{random.randint(1000, 9999)}"
        }
        
        self.client.post(
            "/api/v1/settings/commodities",
            json=commodity_data,
            headers=self._get_headers(),
            name="/api/v1/settings/commodities [CREATE]"
        )
    
    @task(10)
    def create_location(self):
        """Create new location (10% of requests)."""
        location_data = {
            "code": f"LOC-{random.randint(1000, 9999)}",
            "name": f"Test Location {random.randint(1, 1000)}",
            "type": random.choice(["WAREHOUSE", "FACTORY", "PORT"]),
            "country": "IN",
            "state": random.choice(["GJ", "MH", "RJ", "MP"]),
            "city": "TestCity"
        }
        
        self.client.post(
            "/api/v1/settings/locations",
            json=location_data,
            headers=self._get_headers(),
            name="/api/v1/settings/locations [CREATE]"
        )
    
    @task(5)
    def update_commodity(self):
        """Update commodity (5% of requests)."""
        commodity_name = random.choice(TEST_COMMODITIES)
        update_data = {
            "description": f"Updated at {int(time.time())}"
        }
        
        self.client.patch(
            f"/api/v1/settings/commodities/{commodity_name}",
            json=update_data,
            headers=self._get_headers(),
            name="/api/v1/settings/commodities/:id [UPDATE]"
        )
    
    @task(5)
    def update_location(self):
        """Update location (5% of requests)."""
        location_code = random.choice(TEST_LOCATIONS)
        update_data = {
            "name": f"Updated Location {int(time.time())}"
        }
        
        self.client.patch(
            f"/api/v1/settings/locations/{location_code}",
            json=update_data,
            headers=self._get_headers(),
            name="/api/v1/settings/locations/:id [UPDATE]"
        )
    
    # ==================== SEARCH/FILTER OPERATIONS (20%) ====================
    
    @task(10)
    def search_commodities(self):
        """Search commodities (10% of requests)."""
        search_params = {
            "category": random.choice(["COTTON", "GRAIN", "SEED"]),
            "limit": 20
        }
        
        self.client.get(
            "/api/v1/settings/commodities",
            params=search_params,
            headers=self._get_headers(),
            name="/api/v1/settings/commodities [SEARCH]"
        )
    
    @task(10)
    def filter_locations(self):
        """Filter locations (10% of requests)."""
        filter_params = {
            "type": random.choice(["WAREHOUSE", "FACTORY", "PORT"]),
            "state": random.choice(["GJ", "MH", "RJ"]),
            "limit": 20
        }
        
        self.client.get(
            "/api/v1/settings/locations",
            params=filter_params,
            headers=self._get_headers(),
            name="/api/v1/settings/locations [FILTER]"
        )


# ==================== CUSTOM METRICS ====================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics tracking."""
    print("\n" + "="*80)
    print("Commodity ERP Load Test Starting")
    print("="*80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users if hasattr(environment, 'parsed_options') else 'N/A'}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary after test stops."""
    stats = environment.stats
    
    print("\n" + "="*80)
    print("Commodity ERP Load Test Results")
    print("="*80)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"Avg Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"50th Percentile: {stats.total.get_response_time_percentile(0.50):.2f}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print("="*80)
    
    # Success criteria
    success = True
    issues = []
    
    if stats.total.fail_ratio > 0.01:  # More than 1% failure
        success = False
        issues.append(f"High failure rate: {stats.total.fail_ratio * 100:.2f}%")
    
    if stats.total.avg_response_time > 200:  # Avg > 200ms
        success = False
        issues.append(f"High avg response time: {stats.total.avg_response_time:.2f}ms")
    
    if stats.total.get_response_time_percentile(0.95) > 500:  # 95th > 500ms
        success = False
        issues.append(f"High 95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    
    print("\nSUCCESS CRITERIA:")
    print(f"✓ Failure Rate < 1%: {'PASS' if stats.total.fail_ratio <= 0.01 else 'FAIL'}")
    print(f"✓ Avg Response < 200ms: {'PASS' if stats.total.avg_response_time <= 200 else 'FAIL'}")
    print(f"✓ 95th Percentile < 500ms: {'PASS' if stats.total.get_response_time_percentile(0.95) <= 500 else 'FAIL'}")
    
    if success:
        print("\n✅ LOAD TEST PASSED - System ready for production!")
    else:
        print("\n❌ LOAD TEST FAILED - Issues found:")
        for issue in issues:
            print(f"   - {issue}")
    
    print("="*80 + "\n")
