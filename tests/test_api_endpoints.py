"""
Test script for Phase 6 API endpoints
"""

import requests
import json
import time
from uuid import uuid4

BASE_URL = "http://localhost:8080"

def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_root():
    """Test root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_stats():
    """Test stats endpoint"""
    print("\n=== Testing Stats Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/stats")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat():
    """Test chat endpoint"""
    print("\n=== Testing Chat Endpoint ===")
    try:
        # Create a proper request with messages
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": "What is the status of SO-1001?",
                    "timestamp": None
                }
            ],
            "session_id": str(uuid4()),
            "user_id": "test-user-123",
            "max_tokens": 1000,
            "temperature": 0.7,
            "retrieve_memories": True,
            "max_memories": 10,
            "create_memories": True
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_memory():
    """Test memory endpoint"""
    print("\n=== Testing Memory Endpoint ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/memory",
            params={"user_id": "test-user-123", "limit": 10}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_entities():
    """Test entities endpoint"""
    print("\n=== Testing Entities Endpoint ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/entities",
            params={"user_id": "test-user-123", "limit": 10}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Phase 6 API Endpoints")
    print("=" * 50)
    
    # Note: These tests require the API server to be running
    # Run: uvicorn api.main:app --reload --port 8080
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Stats Endpoint", test_stats),
        ("Chat Endpoint", test_chat),
        ("Memory Endpoint", test_memory),
        ("Entities Endpoint", test_entities),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append((name, False))
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
