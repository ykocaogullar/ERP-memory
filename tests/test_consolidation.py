#!/usr/bin/env python3
"""
Test script for Phase 7: Consolidation Service

Tests the consolidation functionality including:
- Session creation and management
- Memory consolidation
- Summary generation
- API endpoints
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
from uuid import uuid4
from api.services.consolidation import get_consolidation_service
from api.utils.database import db
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8080"

def test_consolidation_service():
    """Test the consolidation service directly"""
    print("🧪 Testing Consolidation Service Directly")
    print("=" * 50)
    
    try:
        consolidation_service = get_consolidation_service()
        
        # Test user
        test_user = "consolidation-test-user"
        
        # Get stats before consolidation
        stats_before = consolidation_service.get_consolidation_stats(test_user)
        print(f"📊 Stats before consolidation:")
        print(f"  - Unconsolidated sessions: {stats_before['unconsolidated_sessions']}")
        print(f"  - Consolidated sessions: {stats_before['consolidated_sessions']}")
        print(f"  - Total summaries: {stats_before['total_summaries']}")
        print(f"  - Ready for consolidation: {stats_before['ready_for_consolidation']}")
        
        # Test consolidation
        if stats_before['unconsolidated_sessions'] > 0:
            print(f"\n🔄 Running consolidation...")
            result = consolidation_service.consolidate_sessions(test_user, window_size=3)
            
            print(f"✅ Consolidation completed:")
            print(f"  - Summary IDs: {result['summary_ids']}")
            print(f"  - Session window: {result['session_window']}")
            print(f"  - Consolidated memories: {result['consolidated_memory_count']}")
            print(f"  - Sessions processed: {result['session_count']}")
            print(f"  - Summaries created: {result['summary_count']}")
            
            # Get stats after consolidation
            stats_after = consolidation_service.get_consolidation_stats(test_user)
            print(f"\n📊 Stats after consolidation:")
            print(f"  - Unconsolidated sessions: {stats_after['unconsolidated_sessions']}")
            print(f"  - Consolidated sessions: {stats_after['consolidated_sessions']}")
            print(f"  - Total summaries: {stats_after['total_summaries']}")
        else:
            print(f"⚠️  No sessions available for consolidation")
            
        return True
        
    except Exception as e:
        print(f"❌ Consolidation service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_consolidation_api():
    """Test the consolidation API endpoints"""
    print("\n🌐 Testing Consolidation API Endpoints")
    print("=" * 50)
    
    test_user = "api-test-user"
    
    try:
        # Test stats endpoint
        print("📊 Testing consolidation stats endpoint...")
        stats_response = requests.get(f"{API_BASE_URL}/api/v1/consolidate/stats", params={"user_id": test_user})
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"✅ Stats endpoint successful:")
            print(f"  - Unconsolidated sessions: {stats['unconsolidated_sessions']}")
            print(f"  - Consolidated sessions: {stats['consolidated_sessions']}")
            print(f"  - Total summaries: {stats['total_summaries']}")
            print(f"  - Ready for consolidation: {stats['ready_for_consolidation']}")
        else:
            print(f"❌ Stats endpoint failed: {stats_response.status_code} - {stats_response.text}")
            return False
        
        # Test consolidation endpoint
        if stats['unconsolidated_sessions'] > 0:
            print(f"\n🔄 Testing consolidation endpoint...")
            consolidate_payload = {
                "user_id": test_user,
                "window_size": 3
            }
            
            consolidate_response = requests.post(
                f"{API_BASE_URL}/api/v1/consolidate",
                json=consolidate_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if consolidate_response.status_code == 200:
                result = consolidate_response.json()
                print(f"✅ Consolidation endpoint successful:")
                print(f"  - Summary IDs: {result['summary_ids']}")
                print(f"  - Session window: {result['session_window']}")
                print(f"  - Consolidated memories: {result['consolidated_memory_count']}")
                print(f"  - Sessions processed: {result['session_count']}")
                print(f"  - Summaries created: {result['summary_count']}")
            else:
                print(f"❌ Consolidation endpoint failed: {consolidate_response.status_code} - {consolidate_response.text}")
                return False
        else:
            print(f"⚠️  No sessions available for consolidation via API")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_sessions_and_memories():
    """Create test sessions and memories for consolidation testing"""
    print("\n🏗️  Creating Test Sessions and Memories")
    print("=" * 50)
    
    test_user = "consolidation-test-user"
    
    try:
        # Create 3 test sessions
        session_ids = []
        for i in range(3):
            session_id = str(uuid4())
            session_ids.append(session_id)
            
            # Create session
            session_query = """
                INSERT INTO app.sessions (session_id, user_id, started_at, last_activity_at, turn_count, consolidated)
                VALUES (%s, %s, NOW() - INTERVAL '%s hours', NOW() - INTERVAL '%s hours', 5, false)
            """
            db.execute_update(session_query, (session_id, test_user, i*2, i*2))
            
            # Create memories for this session
            memories_query = """
                INSERT INTO app.memories (session_id, user_id, kind, text, importance, created_at, content_hash)
                VALUES (%s, %s, %s, %s, %s, NOW() - INTERVAL '%s hours', %s)
            """
            
            # Create 2-3 memories per session
            memory_texts = [
                f"User asked about order status for session {i+1}",
                f"Assistant provided order information for session {i+1}",
                f"User requested follow-up for session {i+1}"
            ]
            
            for j, text in enumerate(memory_texts):
                content_hash = f"hash_{session_id}_{j}"
                db.execute_update(memories_query, (
                    session_id, test_user, 'episodic', text, 0.7, i*2, content_hash
                ))
        
        print(f"✅ Created {len(session_ids)} test sessions with memories")
        print(f"  - Session IDs: {session_ids}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_workflow():
    """Test the complete consolidation workflow"""
    print("\n🔄 Testing Complete Consolidation Workflow")
    print("=" * 50)
    
    try:
        # Step 1: Create test data
        if not create_test_sessions_and_memories():
            return False
        
        # Step 2: Test service directly
        if not test_consolidation_service():
            return False
        
        # Step 3: Test API endpoints
        if not test_consolidation_api():
            return False
        
        print("\n🎉 All consolidation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    try:
        # Delete test sessions and related data
        cleanup_query = """
            DELETE FROM app.sessions WHERE user_id LIKE '%test-user%';
            DELETE FROM app.memories WHERE user_id LIKE '%test-user%';
            DELETE FROM app.memory_summaries WHERE user_id LIKE '%test-user%';
        """
        db.execute_update(cleanup_query)
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"⚠️  Cleanup failed: {e}")

if __name__ == "__main__":
    print("🧪 Phase 7: Consolidation Service Tests")
    print("=" * 60)
    
    try:
        # Run tests
        success = test_full_workflow()
        
        if success:
            print("\n✅ All Phase 7 tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some Phase 7 tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cleanup_test_data()
