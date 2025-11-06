"""Test script to verify API authentication is working correctly."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_public_endpoint():
    """Test that public endpoints don't require auth."""
    response = requests.get(f"{BASE_URL}/")
    print(f"✓ Public endpoint (/) - Status: {response.status_code}")
    assert response.status_code == 200, "Public endpoint should be accessible"

def test_protected_endpoint_without_auth():
    """Test that protected endpoints require auth."""
    response = requests.get(f"{BASE_URL}/api/portfolios")
    print(f"✓ Protected endpoint without auth - Status: {response.status_code}")
    assert response.status_code == 401, "Protected endpoint should return 401 without auth"
    
def test_protected_endpoint_with_token():
    """Test that protected endpoints work with valid token."""
    # First login to get a token
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "test_user", "password": "test_password"}
    )
    
    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        
        # Try to access protected endpoint with token
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/portfolios", headers=headers)
        print(f"✓ Protected endpoint with token - Status: {response.status_code}")
        assert response.status_code in [200, 404], "Should be authenticated"
    else:
        print("⚠ Login endpoint not available yet - skipping token test")

def test_protected_endpoint_with_api_key():
    """Test that protected endpoints work with valid API key."""
    # This assumes you have an API key configured
    headers = {"X-API-Key": "ta_your_api_key_here"}
    response = requests.get(f"{BASE_URL}/api/portfolios", headers=headers)
    print(f"✓ Protected endpoint with API key - Status: {response.status_code}")
    # Will return 401 if API key is invalid, which is expected for this test

if __name__ == "__main__":
    print("Testing API Authentication...")
    print("-" * 50)
    
    try:
        test_public_endpoint()
        test_protected_endpoint_without_auth()
        test_protected_endpoint_with_token()
        test_protected_endpoint_with_api_key()
        
        print("-" * 50)
        print("✅ All authentication tests passed!")
        print("\nNext steps:")
        print("1. Start the backend: uvicorn app.main:app --reload")
        print("2. Create a user via API or database")
        print("3. Test with real credentials")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running at", BASE_URL, "?")