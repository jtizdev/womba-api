"""
Womba API - FastAPI wrapper for Womba test generation

This API serves as the central service for all Womba clients:
- Go CLI
- Java CLI
- Node.js CLI
- Atlassian Forge Plugin

Architecture:
    Client (any language) -> Womba API (this) -> Womba Core (Python)
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

# Add womba package to path
WOMBA_PATH = Path(__file__).parent.parent / "womba"
sys.path.insert(0, str(WOMBA_PATH))

from src.aggregator.story_collector import StoryCollector
from src.ai.test_plan_generator import TestPlanGenerator
from src.ai.quality_scorer import TestQualityScorer
from src.integrations.zephyr_integration import ZephyrIntegration
from src.config.settings import settings

# Initialize FastAPI app
app = FastAPI(
    title="Womba API",
    version="1.0.0",
    description="AI-powered test generation service for Jira stories",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for Forge plugin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logger.add(
    "logs/api_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
)


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateRequest(BaseModel):
    """Request to generate test cases for a Jira story"""
    story_key: str = Field(..., description="Jira story key (e.g., PLAT-12991)")
    upload_to_zephyr: bool = Field(default=False, description="Automatically upload to Zephyr")
    
    class Config:
        json_schema_extra = {
            "example": {
                "story_key": "PLAT-12991",
                "upload_to_zephyr": True
            }
        }


class TestCaseModel(BaseModel):
    """Test case model for API response"""
    title: str
    description: str
    steps: List[Dict[str, str]]
    preconditions: Optional[str] = None
    expected_result: str
    priority: str
    test_type: str


class GenerateResponse(BaseModel):
    """Response from test generation"""
    story_key: str
    test_cases: List[Dict[str, Any]]
    quality_score: float
    suggested_folder: str
    execution_time_seconds: float
    zephyr_ids: Optional[List[str]] = None
    metadata: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "story_key": "PLAT-12991",
                "test_cases": [
                    {
                        "title": "Verify user can create policy",
                        "description": "Test policy creation flow",
                        "steps": [
                            {"action": "Navigate to policies", "expected": "Policy page loads"},
                            {"action": "Click Create", "expected": "Form appears"}
                        ],
                        "priority": "High",
                        "test_type": "Functional"
                    }
                ],
                "quality_score": 88.5,
                "suggested_folder": "Orchestration WS/Policies",
                "execution_time_seconds": 12.3,
                "zephyr_ids": ["T123", "T124"],
                "metadata": {
                    "test_count": 8,
                    "ai_model": "gpt-4o",
                    "confluence_pages": 3,
                    "api_endpoints_analyzed": 5
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    dependencies: Dict[str, str]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str
    status_code: int


# ============================================================================
# Authentication
# ============================================================================

def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """Verify API key from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Authorization: Bearer <your-api-key>"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format. Use: Bearer <your-api-key>"
        )
    
    api_key = authorization.split(" ")[1]
    
    # Validate against environment variable
    expected_key = os.getenv("WOMBA_API_KEY")
    if not expected_key:
        logger.error("WOMBA_API_KEY not set in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "Womba API - AI-powered test generation",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        dependencies={
            "jira": "connected" if settings.jira_api_token else "not_configured",
            "openai": "connected" if settings.openai_api_key else "not_configured",
            "zephyr": "connected" if settings.zephyr_api_token else "not_configured",
        }
    )


@app.post("/api/v1/generate", response_model=GenerateResponse)
async def generate_tests(
    request: GenerateRequest,
    authorization: str = Header(None)
):
    """
    Generate AI test cases for a Jira story
    
    This endpoint:
    1. Fetches Jira story details (description, subtasks, comments)
    2. Fetches related Confluence pages
    3. Analyzes API documentation
    4. Fetches existing Zephyr test cases
    5. Generates test cases using AI
    6. Scores quality of generated tests
    7. Optionally uploads to Zephyr
    
    Returns:
        GenerateResponse with test cases, quality score, and metadata
    """
    # Verify authentication
    verify_api_key(authorization)
    
    start_time = time.time()
    logger.info(f"Generating tests for {request.story_key}")
    
    try:
        # 1. Collect story context
        logger.info("Step 1: Collecting story context...")
        collector = StoryCollector()
        context = await collector.collect_story_context(request.story_key)
        
        # 2. Generate test plan
        logger.info("Step 2: Generating test plan with AI...")
        generator = TestPlanGenerator()
        test_plan = await generator.generate_test_plan(context)
        
        # 3. Score quality
        logger.info("Step 3: Scoring test quality...")
        scorer = TestQualityScorer()
        quality_results = scorer.score_test_plan(
            test_plan.test_cases,
            test_plan.story
        )
        
        # 4. Upload to Zephyr if requested
        zephyr_ids = []
        if request.upload_to_zephyr:
            logger.info("Step 4: Uploading to Zephyr...")
            zephyr = ZephyrIntegration()
            
            for test_case in test_plan.test_cases:
                try:
                    result = await zephyr.create_test_case(
                        test_case,
                        request.story_key
                    )
                    zephyr_ids.append(result.get('key', 'unknown'))
                except Exception as e:
                    logger.error(f"Failed to upload test case: {e}")
                    # Continue with other test cases
        
        execution_time = time.time() - start_time
        
        logger.info(
            f"✅ Generated {len(test_plan.test_cases)} tests in {execution_time:.2f}s "
            f"(Quality: {quality_results['average_score']:.1f}/100)"
        )
        
        # Build response
        return GenerateResponse(
            story_key=request.story_key,
            test_cases=[tc.dict() for tc in test_plan.test_cases],
            quality_score=quality_results['average_score'],
            suggested_folder=test_plan.suggested_folder or "AI Generated Tests",
            execution_time_seconds=round(execution_time, 2),
            zephyr_ids=zephyr_ids if zephyr_ids else None,
            metadata={
                "test_count": len(test_plan.test_cases),
                "ai_model": settings.ai_model,
                "confluence_pages": len(context.get('confluence_pages', [])),
                "api_endpoints_analyzed": len(context.get('api_endpoints', [])),
                "existing_tests_analyzed": len(context.get('existing_tests', [])),
            }
        )
    
    except Exception as e:
        logger.error(f"Generation failed for {request.story_key}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test generation failed: {str(e)}"
        )


@app.get("/api/v1/story/{story_key}")
async def get_story_info(
    story_key: str,
    authorization: str = Header(None)
):
    """Get basic info about a Jira story (for debugging)"""
    verify_api_key(authorization)
    
    try:
        collector = StoryCollector()
        context = await collector.collect_story_context(story_key)
        
        return {
            "story_key": story_key,
            "title": context.get('title', 'Unknown'),
            "status": context.get('status', 'Unknown'),
            "confluence_pages": len(context.get('confluence_pages', [])),
            "subtasks": len(context.get('subtasks', [])),
            "comments": len(context.get('comments', [])),
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch story: {str(e)}"
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "detail": str(exc)
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "status_code": 500,
        "detail": str(exc)
    }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Womba API starting up...")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"Jira URL: {settings.jira_base_url}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Womba API shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )

