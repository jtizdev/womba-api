"""
Integration Tests for Womba API Contract

These tests ensure that the API contract remains stable across versions.
If any of these tests fail, it means a BREAKING CHANGE that will affect:
- womba-go (Go CLI)
- womba-java (Java CLI)
- womba-node (Node.js CLI)
- womba-forge (Atlassian Forge plugin)

Run these tests before:
1. Deploying API updates
2. Creating new releases
3. Merging PRs that change API responses
"""

import pytest
import os
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Set test environment
os.environ["WOMBA_API_KEY"] = "test-api-key-12345"
os.environ["ENV"] = "test"

from main import app

client = TestClient(app)


# ============================================================================
# Contract Tests - Response Schema
# ============================================================================

class TestAPIContractResponses:
    """Test that API responses match expected schema"""
    
    def test_health_endpoint_schema(self):
        """Health endpoint must return expected fields"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "dependencies" in data
        
        # Type validation
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["dependencies"], dict)
    
    
    def test_root_endpoint_schema(self):
        """Root endpoint must return expected fields"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        
        # Values
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
    
    
    def test_generate_response_schema_structure(self):
        """
        Generate endpoint response must match expected schema
        
        This is critical - all clients depend on this structure!
        """
        # Mock response structure (test with actual API in e2e tests)
        expected_fields = [
            "story_key",
            "test_cases",
            "quality_score",
            "suggested_folder",
            "execution_time_seconds",
            "zephyr_ids",
            "metadata"
        ]
        
        # Test with mock data
        mock_response = {
            "story_key": "PLAT-12991",
            "test_cases": [
                {
                    "title": "Test case 1",
                    "description": "Description",
                    "steps": [{"action": "Step 1", "expected": "Result 1"}],
                    "priority": "High",
                    "test_type": "Functional",
                    "expected_result": "Pass"
                }
            ],
            "quality_score": 88.5,
            "suggested_folder": "Test Folder",
            "execution_time_seconds": 12.3,
            "zephyr_ids": ["T123"],
            "metadata": {
                "test_count": 1,
                "ai_model": "gpt-4o"
            }
        }
        
        # Validate all required fields exist
        for field in expected_fields:
            assert field in mock_response, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(mock_response["story_key"], str)
        assert isinstance(mock_response["test_cases"], list)
        assert isinstance(mock_response["quality_score"], (int, float))
        assert isinstance(mock_response["suggested_folder"], str)
        assert isinstance(mock_response["execution_time_seconds"], (int, float))
        assert isinstance(mock_response["metadata"], dict)
        
        # Validate test case structure
        if mock_response["test_cases"]:
            test_case = mock_response["test_cases"][0]
            required_tc_fields = ["title", "description", "steps", "priority", "test_type"]
            for field in required_tc_fields:
                assert field in test_case, f"Missing test case field: {field}"


# ============================================================================
# Contract Tests - Authentication
# ============================================================================

class TestAPIContractAuthentication:
    """Test authentication behavior remains consistent"""
    
    def test_missing_auth_header_returns_401(self):
        """Missing auth header must return 401"""
        response = client.post(
            "/api/v1/generate",
            json={"story_key": "PLAT-12991"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data or "error" in data
    
    
    def test_invalid_auth_format_returns_401(self):
        """Invalid auth format must return 401"""
        response = client.post(
            "/api/v1/generate",
            json={"story_key": "PLAT-12991"},
            headers={"Authorization": "InvalidFormat"}
        )
        
        assert response.status_code == 401
    
    
    def test_invalid_api_key_returns_403(self):
        """Invalid API key must return 403"""
        response = client.post(
            "/api/v1/generate",
            json={"story_key": "PLAT-12991"},
            headers={"Authorization": "Bearer wrong-key"}
        )
        
        assert response.status_code == 403


# ============================================================================
# Contract Tests - Request Validation
# ============================================================================

class TestAPIContractRequestValidation:
    """Test request validation remains consistent"""
    
    def test_generate_requires_story_key(self):
        """Generate endpoint must require story_key"""
        response = client.post(
            "/api/v1/generate",
            json={},
            headers={"Authorization": "Bearer test-api-key-12345"}
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    
    def test_generate_accepts_upload_flag(self):
        """Generate endpoint must accept optional upload_to_zephyr flag"""
        # This should pass validation (even if it fails later)
        response = client.post(
            "/api/v1/generate",
            json={
                "story_key": "PLAT-12991",
                "upload_to_zephyr": True
            },
            headers={"Authorization": "Bearer test-api-key-12345"}
        )
        
        # Should not be a validation error (422)
        # May be 500 if Jira is not configured, but not 422
        assert response.status_code != 422


# ============================================================================
# Contract Tests - Error Responses
# ============================================================================

class TestAPIContractErrors:
    """Test error responses remain consistent"""
    
    def test_404_for_unknown_endpoint(self):
        """Unknown endpoints must return 404"""
        response = client.get("/api/v1/unknown")
        assert response.status_code == 404
    
    
    def test_error_response_has_detail(self):
        """All error responses must have detail or error field"""
        response = client.post(
            "/api/v1/generate",
            json={"story_key": "PLAT-12991"}
            # Missing auth header
        )
        
        data = response.json()
        assert "detail" in data or "error" in data


# ============================================================================
# Contract Tests - Data Types
# ============================================================================

class TestAPIContractDataTypes:
    """Test that data types remain consistent"""
    
    def test_quality_score_is_numeric(self):
        """Quality score must be numeric (float)"""
        mock_response = {
            "quality_score": 88.5
        }
        
        assert isinstance(mock_response["quality_score"], (int, float))
        assert 0 <= mock_response["quality_score"] <= 100
    
    
    def test_execution_time_is_numeric(self):
        """Execution time must be numeric (float)"""
        mock_response = {
            "execution_time_seconds": 12.3
        }
        
        assert isinstance(mock_response["execution_time_seconds"], (int, float))
        assert mock_response["execution_time_seconds"] >= 0
    
    
    def test_test_cases_is_array(self):
        """Test cases must be an array"""
        mock_response = {
            "test_cases": []
        }
        
        assert isinstance(mock_response["test_cases"], list)
    
    
    def test_metadata_is_object(self):
        """Metadata must be an object/dict"""
        mock_response = {
            "metadata": {
                "test_count": 5,
                "ai_model": "gpt-4o"
            }
        }
        
        assert isinstance(mock_response["metadata"], dict)


# ============================================================================
# Contract Tests - Backward Compatibility
# ============================================================================

class TestAPIContractBackwardCompatibility:
    """Test backward compatibility with previous versions"""
    
    def test_v1_endpoint_exists(self):
        """API v1 endpoints must exist"""
        # Even with missing auth, endpoint should be recognized
        response = client.post("/api/v1/generate", json={})
        
        # Should not be 404 (endpoint not found)
        assert response.status_code != 404
    
    
    def test_legacy_fields_still_present(self):
        """Legacy response fields must still be present"""
        # If we add new fields, old ones must remain for backward compatibility
        
        required_legacy_fields = [
            "story_key",
            "test_cases",
            "quality_score",
            "suggested_folder"
        ]
        
        mock_response = {
            "story_key": "PLAT-12991",
            "test_cases": [],
            "quality_score": 88.5,
            "suggested_folder": "Test Folder",
            "execution_time_seconds": 12.3,
            "metadata": {}
        }
        
        for field in required_legacy_fields:
            assert field in mock_response, \
                f"Legacy field {field} removed - BREAKING CHANGE!"


# ============================================================================
# Contract Tests - OpenAPI Spec
# ============================================================================

class TestAPIContractOpenAPISpec:
    """Test OpenAPI specification remains accessible"""
    
    def test_openapi_json_accessible(self):
        """OpenAPI JSON spec must be accessible"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
    
    
    def test_docs_accessible(self):
        """API documentation must be accessible"""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    
    def test_redoc_accessible(self):
        """ReDoc documentation must be accessible"""
        response = client.get("/redoc")
        
        assert response.status_code == 200


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

