# Womba API Testing Guide

## Overview

This guide explains how to run integration tests to ensure that changes to the Python package don't break the API contract for client implementations.

## Test Types

### 1. Contract Tests (Critical!)

**Purpose**: Ensure API response schema remains stable across versions.

**When to run**:
- Before every deployment
- Before merging PRs
- After changing response models

**How to run**:
```bash
pytest tests/test_api_contract.py -v
```

**What it tests**:
- Response field presence and types
- Authentication behavior
- Request validation
- Error response structure
- Backward compatibility

**If tests fail**: You have a BREAKING CHANGE that will affect all clients!

### 2. E2E Integration Tests

**Purpose**: Test full pipeline with real dependencies (Jira, AI, Zephyr).

**When to run**:
- Before major releases
- After significant logic changes
- In staging environment

**Setup**:
```bash
# Configure test environment
export TEST_STORY_KEY=PLAT-12991
export RUN_E2E_TESTS=true

# Copy .env with real credentials
cp .env.example .env
# Edit .env with your test credentials
```

**How to run**:
```bash
# All E2E tests
pytest tests/test_e2e_integration.py -v -s

# Specific test
pytest tests/test_e2e_integration.py::TestE2EFullWorkflow::test_generate_tests_without_upload -v
```

**What it tests**:
- Full Jira → AI → Zephyr pipeline
- Performance requirements (<60s)
- Data quality standards
- Client simulations (Go, Java, Node.js)

### 3. Client Simulation Tests

**Purpose**: Simulate requests from different language clients.

**What it tests**:
- Go client compatibility
- Java client compatibility
- Node.js client compatibility
- Forge plugin compatibility

**How to run**:
```bash
pytest tests/test_e2e_integration.py::TestE2EClientSimulation -v
```

## CI/CD Integration

### GitHub Actions Workflow

The API has automated contract tests that run on every PR:

**File**: `.github/workflows/contract-tests.yml`

**What it does**:
1. Runs contract tests on every push/PR
2. If tests fail, auto-creates issues in client repos:
   - womba-go
   - womba-java
   - womba-node
   - womba-forge

**How it works**:
```yaml
# Trigger on push or PR
on: [push, pull_request]

# Steps:
1. Checkout womba-api
2. Checkout womba (core package)
3. Install dependencies
4. Run contract tests
5. If fail → notify client repos
```

## Pre-Deployment Checklist

Before deploying changes to production:

- [ ] All contract tests pass
- [ ] E2E tests pass in staging
- [ ] No breaking changes to API schema
- [ ] Version bumped if needed
- [ ] Changelog updated
- [ ] Client repos reviewed for compatibility

## Breaking Change Protocol

If you MUST make a breaking change:

1. **Document the change**:
   - Update CHANGELOG.md
   - Add migration guide

2. **Version bump**:
   - Major version bump (1.0.0 → 2.0.0)

3. **Notify clients**:
   - Create issues in all client repos
   - Provide migration examples

4. **Deprecation period**:
   - Keep old endpoint for 1 version
   - Add deprecation warnings

5. **Update all clients**:
   - womba-go
   - womba-java
   - womba-node
   - womba-forge

## Local Testing Workflow

### Quick Test (5 minutes)
```bash
# Run contract tests only
pytest tests/test_api_contract.py -v
```

### Full Test (20 minutes)
```bash
# Run all tests
export RUN_E2E_TESTS=true
export TEST_STORY_KEY=PLAT-12991
pytest tests/ -v -s
```

### Manual API Test
```bash
# Start API locally
uvicorn main:app --reload --port 8000

# Test in another terminal
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"story_key": "PLAT-12991", "upload_to_zephyr": false}'
```

## Debugging Failed Tests

### Contract Test Failures

**Error**: "Missing required field: X"
```bash
# Solution: Field was removed - BREAKING CHANGE
# Action: Restore field or bump major version
```

**Error**: "Invalid type for field X"
```bash
# Solution: Type changed - BREAKING CHANGE
# Action: Restore type or bump major version
```

### E2E Test Failures

**Error**: "Jira connection failed"
```bash
# Solution: Check .env credentials
# Verify: curl -u email:token https://your-jira.atlassian.net/rest/api/3/myself
```

**Error**: "Generation too slow"
```bash
# Solution: Optimize AI prompts or increase timeout
# Check: logs/api_*.log for bottlenecks
```

**Error**: "Quality score too low"
```bash
# Solution: Improve AI prompts
# Review: Generated test cases for issues
```

## Test Coverage Goals

- **Contract tests**: 100% API schema coverage
- **E2E tests**: 70% happy path coverage
- **Error tests**: 50% error scenario coverage

## Reporting Issues

If tests fail consistently:

1. Check logs: `logs/api_*.log`
2. Create issue with:
   - Test name
   - Error message
   - Environment details
   - Steps to reproduce

## FAQ

**Q: Why are contract tests so important?**
A: They ensure API stability for ALL clients (Go, Java, Node.js, Forge). One failure = breaking change for all customers.

**Q: Can I skip E2E tests locally?**
A: Yes, set `RUN_E2E_TESTS=false` (default). But CI will run them.

**Q: How do I test Zephyr upload?**
A: Set `TEST_ZEPHYR_UPLOAD=true` (careful - creates real test cases!)

**Q: What if I need to make a breaking change?**
A: Follow the "Breaking Change Protocol" above. Version bump + migration guide.
