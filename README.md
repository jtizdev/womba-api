# Womba API

FastAPI service that wraps the Womba Python CLI and provides a REST API for multi-language clients.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Womba API (Python)                   │
│              FastAPI REST Service (Hosted)               │
│         Core: Jira, AI, Zephyr, Quality Scoring         │
└─────────────────────────────────────────────────────────┘
                           ↑
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  womba-go     │  │  womba-java   │  │  womba-node   │
│  (Go CLI)     │  │  (Java CLI)   │  │  (Node CLI)   │
│  HTTP client  │  │  HTTP client  │  │  HTTP client  │
└───────────────┘  └───────────────┘  └───────────────┘
                           ↑
                  ┌────────────────────┐
                  │   womba-forge      │
                  │  (Forge Plugin)    │
                  │  Jira UI Panel     │
                  └────────────────────┘
```

## Features

- **REST API** for test generation
- **Multi-language support** (Go, Java, Node.js, Forge)
- **API contract tests** to prevent breaking changes
- **Quality scoring** for generated tests
- **Zephyr integration** for automatic test upload
- **OpenAPI documentation** (Swagger/ReDoc)

## Quick Start

### 1. Prerequisites

```bash
# Clone both repos
git clone https://github.com/jtizdev/womba-api.git
git clone https://github.com/jtizdev/womba.git

cd womba-api
```

### 2. Install Dependencies

```bash
# Install API dependencies
pip install -r requirements.txt

# Install womba package in development mode
pip install -e ../womba
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 4. Run the API

```bash
# Development mode
uvicorn main:app --reload --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Generate tests
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"story_key": "PLAT-12991", "upload_to_zephyr": false}'
```

## API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### POST `/api/v1/generate`

Generate test cases for a Jira story.

**Request:**
```json
{
  "story_key": "PLAT-12991",
  "upload_to_zephyr": false
}
```

**Response:**
```json
{
  "story_key": "PLAT-12991",
  "test_cases": [
    {
      "title": "Verify user can create policy",
      "description": "Test policy creation flow",
      "steps": [
        {"action": "Navigate to policies", "expected": "Policy page loads"}
      ],
      "priority": "High",
      "test_type": "Functional"
    }
  ],
  "quality_score": 88.5,
  "suggested_folder": "Orchestration WS/Policies",
  "execution_time_seconds": 12.3,
  "metadata": {
    "test_count": 8,
    "ai_model": "gpt-4o"
  }
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-18 12:00:00",
  "dependencies": {
    "jira": "connected",
    "openai": "connected",
    "zephyr": "connected"
  }
}
```

## Testing

### Contract Tests (Critical!)

These tests ensure API contract stability for all clients:

```bash
# Run contract tests
pytest tests/test_api_contract.py -v

# These tests MUST pass before deploying or merging PRs
# Failure = breaking change for Go/Java/Node/Forge clients
```

### E2E Integration Tests

Test the full pipeline with real dependencies:

```bash
# Set test story
export TEST_STORY_KEY=PLAT-12991
export RUN_E2E_TESTS=true

# Run E2E tests
pytest tests/test_e2e_integration.py -v -s

# Test Zephyr upload (careful - creates real test cases!)
export TEST_ZEPHYR_UPLOAD=true
pytest tests/test_e2e_integration.py::TestE2EFullWorkflow::test_generate_tests_with_upload -v
```

### All Tests

```bash
# Run all tests
pytest tests/ -v --tb=short
```

## CI/CD

### GitHub Actions

The API has automated contract tests that run on every PR:

1. **Contract Tests** - Ensure API schema stability
2. **Client Notification** - Auto-create issues in client repos if contract breaks

### Pre-Deployment Checklist

Before deploying changes:

- [ ] All contract tests pass
- [ ] No breaking changes to response schema
- [ ] Version bumped if API changes
- [ ] Changelog updated
- [ ] Client repos notified of changes

## Deployment

### Railway.app (Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Add environment variables
railway variables set WOMBA_API_KEY=your-key
railway variables set JIRA_API_TOKEN=your-token
# ... add all other env vars

# Deploy
railway up

# Get URL
railway domain
```

### Docker

```bash
# Build image
docker build -t womba-api .

# Run container
docker run -p 8000:8000 \
  --env-file .env \
  womba-api

# Or use docker-compose
docker-compose up -d
```

### AWS Lambda (Alternative)

Use Mangum to wrap FastAPI for Lambda:

```python
from mangum import Mangum
handler = Mangum(app)
```

## Client Repositories

This API serves the following clients:

- **womba-go**: Go CLI wrapper
- **womba-java**: Java CLI wrapper  
- **womba-node**: Node.js CLI wrapper
- **womba-forge**: Atlassian Forge plugin

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WOMBA_API_KEY` | Yes | API authentication key |
| `JIRA_BASE_URL` | Yes | Jira instance URL |
| `JIRA_EMAIL` | Yes | Jira user email |
| `JIRA_API_TOKEN` | Yes | Jira API token |
| `ZEPHYR_API_TOKEN` | Yes | Zephyr Scale token |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `CONFLUENCE_BASE_URL` | No | Confluence URL |
| `CONFLUENCE_API_TOKEN` | No | Confluence token |
| `API_DOCS_URL` | No | API documentation URL |
| `PORT` | No | Server port (default: 8000) |

## Security

### API Key Authentication

All endpoints (except `/health` and `/`) require authentication:

```
Authorization: Bearer your-api-key
```

### Best Practices

1. **Never commit `.env`** - Use `.env.example` only
2. **Rotate API keys** regularly
3. **Use HTTPS** in production
4. **Restrict CORS** origins in production
5. **Monitor API usage** for anomalies

## Troubleshooting

### Common Issues

**Issue**: `Module not found: womba`
```bash
# Solution: Install womba package
pip install -e ../womba
```

**Issue**: `Invalid API key`
```bash
# Solution: Set WOMBA_API_KEY in .env
echo "WOMBA_API_KEY=your-key" >> .env
```

**Issue**: `Jira connection failed`
```bash
# Solution: Verify Jira credentials
curl -u email@company.com:api-token https://your-company.atlassian.net/rest/api/3/myself
```

## Contributing

1. Create feature branch
2. Make changes
3. **Run contract tests**: `pytest tests/test_api_contract.py -v`
4. Ensure no breaking changes
5. Submit PR

## License

MIT License - See womba repository for details

## Support

- **Issues**: https://github.com/jtizdev/womba-api/issues
- **Docs**: https://github.com/jtizdev/womba
- **Email**: support@womba.ai

