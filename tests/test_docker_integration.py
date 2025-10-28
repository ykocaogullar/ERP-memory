#!/usr/bin/env python3
"""
Docker Integration Test Script

Tests the containerized ERP Memory System to ensure:
- All services start correctly
- Database is accessible
- API endpoints work
- Health checks pass
"""

import requests
import time
import sys
import subprocess
import json
from uuid import uuid4

API_BASE_URL = "http://localhost:8080"

def test_docker_services():
    """Test that all Docker services are running"""
    print("🐳 Testing Docker Services")
    print("=" * 40)
    
    try:
        # Check if containers are running
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "table"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the table output
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            print("❌ No containers found")
            return False
            
        # Skip header line and count running containers
        running_containers = []
        for line in lines[1:]:
            if line.strip() and 'Up' in line:
                parts = line.split()
                if len(parts) >= 2:
                    container_name = parts[0]
                    status = ' '.join(parts[1:])
                    running_containers.append({'Name': container_name, 'State': status})
        
        print(f"✅ Found {len(running_containers)} running containers:")
        for container in running_containers:
            print(f"   - {container['Name']}: {container['State']}")
        
        # Check for required services
        required_services = ['erp_db', 'erp_api']
        running_names = [c['Name'] for c in running_containers]
        
        for service in required_services:
            if service in running_names:
                print(f"✅ {service} is running")
            else:
                print(f"❌ {service} is not running")
                return False
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker Compose command failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker services: {e}")
        return False

def test_api_health():
    """Test API health endpoint"""
    print("\n🏥 Testing API Health")
    print("=" * 40)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed")
            print(f"   - Status: {health_data.get('status')}")
            print(f"   - Database: {health_data.get('checks', {}).get('database')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check request failed: {e}")
        return False

def test_api_endpoints():
    """Test basic API endpoints"""
    print("\n🌐 Testing API Endpoints")
    print("=" * 40)
    
    endpoints_to_test = [
        ("/", "Root endpoint"),
        ("/stats", "Stats endpoint"),
        ("/api/v1/consolidate/stats?user_id=test", "Consolidation stats")
    ]
    
    success_count = 0
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                success_count += 1
            else:
                print(f"❌ {description}: Failed ({response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: Error ({e})")
    
    return success_count == len(endpoints_to_test)

def test_chat_endpoint():
    """Test the chat endpoint with a simple message"""
    print("\n💬 Testing Chat Endpoint")
    print("=" * 40)
    
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, can you help me?",
                    "timestamp": None
                }
            ],
            "session_id": str(uuid4()),
            "user_id": "docker-test-user",
            "max_tokens": 100,
            "temperature": 0.7,
            "retrieve_memories": True,
            "max_memories": 5,
            "create_memories": True
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            chat_data = response.json()
            print(f"✅ Chat endpoint working")
            print(f"   - Response length: {len(chat_data.get('response', ''))}")
            print(f"   - Session ID: {chat_data.get('session_id')}")
            print(f"   - Memories created: {chat_data.get('memories_created', 0)}")
            return True
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat endpoint request failed: {e}")
        return False

def test_database_connectivity():
    """Test database connectivity through API"""
    print("\n🗄️  Testing Database Connectivity")
    print("=" * 40)
    
    try:
        # Test stats endpoint which queries the database
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Database connectivity confirmed")
            print(f"   - Domain records: {len(stats.get('domain', {}))}")
            print(f"   - App records: {len(stats.get('app', {}))}")
            return True
        else:
            print(f"❌ Database connectivity failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Database connectivity test failed: {e}")
        return False

def main():
    """Run all Docker integration tests"""
    print("🧪 Docker Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Docker Services", test_docker_services),
        ("API Health", test_api_health),
        ("API Endpoints", test_api_endpoints),
        ("Database Connectivity", test_database_connectivity),
        ("Chat Endpoint", test_chat_endpoint)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Docker integration tests passed!")
        print("✅ ERP Memory System is running correctly in Docker")
        return True
    else:
        print("❌ Some tests failed. Check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
