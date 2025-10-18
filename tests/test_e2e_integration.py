"""
End-to-End Integration Tests

These tests run against the actual Womba API with real dependencies.
They ensure that changes to the Python package don't break the API contract.

Prerequisites:
- Valid .env configuration
- Access to Jira/Confluence/Zephyr (test environment)
- OpenAI API key

Run with: pytest tests/test_e2e_integration.py -v --tb=short
"""

import pytest
import os
import json
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Set test API key
os.environ["WOMBA_API_KEY"] = os.getenv("WOMBA_API_KEY", "test-key-for-e2e")

from main import app

client = TestClient(app)


# ============================================================================
# E2E Test Configuration
# ============================================================================

# Test story - use a real story from your Jira
TEST_STORY_KEY = os.getenv("TEST_STORY_KEY", "PLAT-12991")

# Skip E2E tests if not in CI/production testing
SKIP_E2E = not os.getenv("RUN_E2E_TESTS", "false").lower() == "true"

skip_e2e = pytest.mark.skipif(
    SKIP_E2E,
    reason="E2E tests disabled. Set RUN_E2E_TESTS=true to enable"
)


# ============================================================================
# E2E Test Fixtures
# ============================================================================

@pytest.fixture
def auth_headers():
    """Get auth headers for requests"""
    api_key = os.getenv("WOMBA_API_KEY", "test-key-for-e2e")
    return {"Authorization": f"Bearer {api_key}"}


# ============================================================================
# E2E Tests - Full Workflow
# ============================================================================

class TestE2EFullWorkflow:
    """Test complete end-to-end workflow"""
    
    @skip_e2e
    def test_generate_tests_without_upload(self, auth_headers):
        """
        E2E Test: Generate tests without uploading to Zephyr
        
        This tests the full pipeline:
        - Jira story fetch
        - Confluence page retrieval
        - AI generation
        - Quality scoring
        """
        response = client.post(
            "/api/v1/generate",
            json={
                "story_key": TEST_STORY_KEY,
                "upload_to_zephyr": False
            },
            headers=auth_headers,
            timeout=120.0  # AI generation can take time
        )
        
        # Assert successful response
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Validate response structure (contract)
        assert "story_key" in data
        assert "test_cases" in data
        assert "quality_score" in data
        assert "suggested_folder" in data
        assert "execution_time_seconds" in data
        assert "metadata" in data
        
        # Validate data
        assert data["story_key"] == TEST_STORY_KEY
        assert isinstance(data["test_cases"], list)
        assert len(data["test_cases"]) > 0, "No test cases generated"
        
        # Quality score validation
        assert 0 <= data["quality_score"] <= 100
        assert data["quality_score"] >= 70, \
            f"Quality score too low: {data['quality_score']}"
        
        # Validate test case structure
        first_test = data["test_cases"][0]
        required_fields = ["title", "description", "steps", "priority", "test_type"]
        for field in required_fields:
            assert field in first_test, f"Missing field in test case: {field}"
        
        # Validate steps structure
        assert isinstance(first_test["steps"], list)
        assert len(first_test["steps"]) > 0, "Test case has no steps"
        
        # Validate metadata
        metadata = data["metadata"]
        assert "test_count" in metadata
        assert "ai_model" in metadata
        assert metadata["test_count"] == len(data["test_cases"])
        
        print(f"\n✅ E2E Test Passed:")
        print(f"   Story: {TEST_STORY_KEY}")
        print(f"   Tests Generated: {len(data['test_cases'])}")
        print(f"   Quality Score: {data['quality_score']:.1f}/100")
        print(f"   Execution Time: {data['execution_time_seconds']:.2f}s")
        print(f"   Suggested Folder: {data['suggested_folder']}")
    
    
    @skip_e2e
    def test_generate_tests_with_upload(self, auth_headers):
        """
        E2E Test: Generate and upload to Zephyr
        
        WARNING: This will create actual test cases in Zephyr!
        Only run in test environment.
        """
        # Skip if not explicitly enabled
        if not os.getenv("TEST_ZEPHYR_UPLOAD", "false").lower() == "true":
            pytest.skip("Zephyr upload test disabled. Set TEST_ZEPHYR_UPLOAD=true")
        
        response = client.post(
            "/api/v1/generate",
            json={
                "story_key": TEST_STORY_KEY,
                "upload_to_zephyr": True
            },
            headers=auth_headers,
            timeout=180.0  # Upload takes additional time
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Validate Zephyr IDs returned
        assert "zephyr_ids" in data
        assert data["zephyr_ids"] is not None
        assert isinstance(data["zephyr_ids"], list)
        assert len(data["zephyr_ids"]) > 0, "No Zephyr IDs returned"
        
        print(f"\n✅ E2E Upload Test Passed:")
        print(f"   Tests Uploaded: {len(data['zephyr_ids'])}")
        print(f"   Zephyr IDs: {data['zephyr_ids']}")


# ============================================================================
# E2E Tests - Story Info
# ============================================================================

class TestE2EStoryInfo:
    """Test story information endpoint"""
    
    @skip_e2e
    def test_get_story_info(self, auth_headers):
        """E2E Test: Fetch story information"""
        response = client.get(
            f"/api/v1/story/{TEST_STORY_KEY}",
            headers=auth_headers,
            timeout=30.0
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate response
        assert "story_key" in data
        assert "title" in data
        assert "status" in data
        assert data["story_key"] == TEST_STORY_KEY
        
        print(f"\n✅ Story Info Test Passed:")
        print(f"   Title: {data['title']}")
        print(f"   Status: {data['status']}")


# ============================================================================
# E2E Tests - Error Handling
# ============================================================================

class TestE2EErrorHandling:
    """Test error handling in E2E scenarios"""
    
    def test_invalid_story_key(self, auth_headers):
        """E2E Test: Invalid story key should return 500"""
        response = client.post(
            "/api/v1/generate",
            json={
                "story_key": "INVALID-99999",
                "upload_to_zephyr": False
            },
            headers=auth_headers,
            timeout=30.0
        )
        
        # Should fail gracefully
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data or "error" in data


# ============================================================================
# E2E Tests - Performance
# ============================================================================

class TestE2EPerformance:
    """Test performance requirements"""
    
    @skip_e2e
    def test_generation_performance(self, auth_headers):
        """E2E Test: Generation should complete within reasonable time"""
        import time
        
        start = time.time()
        
        response = client.post(
            "/api/v1/generate",
            json={
                "story_key": TEST_STORY_KEY,
                "upload_to_zephyr": False
            },
            headers=auth_headers,
            timeout=120.0
        )
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Performance requirements
        assert elapsed < 60, f"Generation too slow: {elapsed:.2f}s"
        assert data["execution_time_seconds"] < 60, \
            f"Server-side too slow: {data['execution_time_seconds']:.2f}s"
        
        print(f"\n✅ Performance Test Passed:")
        print(f"   Total Time: {elapsed:.2f}s")
        print(f"   Server Time: {data['execution_time_seconds']:.2f}s")


# ============================================================================
# E2E Tests - Data Quality
# ============================================================================

class TestE2EDataQuality:
    """Test quality of generated data"""
    
    @skip_e2e
    def test_generated_test_quality(self, auth_headers):
        """E2E Test: Generated tests must meet quality standards"""
        response = client.post(
            "/api/v1/generate",
            json={
                "story_key": TEST_STORY_KEY,
                "upload_to_zephyr": False
            },
            headers=auth_headers,
            timeout=120.0
        )
        
        assert response.status_code == 200
        data = response.json()
        
        test_cases = data["test_cases"]
        
        # Quality checks
        for i, test_case in enumerate(test_cases):
            # Title should be meaningful
            assert len(test_case["title"]) >= 10, \
                f"Test {i+1} title too short: {test_case['title']}"
            
            # Description should be present
            assert len(test_case["description"]) >= 20, \
                f"Test {i+1} description too short"
            
            # Steps should be detailed
            assert len(test_case["steps"]) >= 2, \
                f"Test {i+1} needs at least 2 steps"
            
            # Each step should have action and expected
            for step in test_case["steps"]:
                assert "action" in step or "description" in step, \
                    f"Step missing action in test {i+1}"
                assert "expected" in step or "expectedResult" in step, \
                    f"Step missing expected result in test {i+1}"
        
        print(f"\n✅ Quality Test Passed:")
        print(f"   All {len(test_cases)} tests meet quality standards")


# ============================================================================
# E2E Tests - Multi-Language Client Simulation
# ============================================================================

class TestE2EClientSimulation:
    """Simulate requests from different language clients"""
    
    @skip_e2e
    def test_go_client_simulation(self, auth_headers):
        """Simulate Go client request"""
        # Go client would send exactly this structure
        go_request = {
            "story_key": TEST_STORY_KEY,
            "upload_to_zephyr": False
        }
        
        response = client.post(
            "/api/v1/generate",
            json=go_request,
            headers=auth_headers,
            timeout=120.0
        )
        
        assert response.status_code == 200
        
        # Go client expects these fields
        data = response.json()
        assert "test_cases" in data
        assert "quality_score" in data
        
        print("✅ Go client simulation: PASS")
    
    
    @skip_e2e
    def test_java_client_simulation(self, auth_headers):
        """Simulate Java client request"""
        # Java client would send exactly this structure
        java_request = {
            "story_key": TEST_STORY_KEY,
            "upload_to_zephyr": True
        }
        
        # Skip actual upload
        java_request["upload_to_zephyr"] = False
        
        response = client.post(
            "/api/v1/generate",
            json=java_request,
            headers=auth_headers,
            timeout=120.0
        )
        
        assert response.status_code == 200
        
        # Java client expects camelCase can be parsed
        data = response.json()
        assert data is not None
        
        print("✅ Java client simulation: PASS")
    
    
    @skip_e2e
    def test_nodejs_client_simulation(self, auth_headers):
        """Simulate Node.js client request"""
        # Node.js client would send exactly this structure
        node_request = {
            "story_key": TEST_STORY_KEY,
            "upload_to_zephyr": False
        }
        
        response = client.post(
            "/api/v1/generate",
            json=node_request,
            headers=auth_headers,
            timeout=120.0
        )
        
        assert response.status_code == 200
        
        # Node.js client expects JSON
        data = response.json()
        assert isinstance(data["test_cases"], list)
        
        print("✅ Node.js client simulation: PASS")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s",  # Show print statements
    ])

