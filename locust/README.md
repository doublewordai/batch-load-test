# Batch API Load Test

Locust-based load testing for the batch inference API.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management.

```bash
# Install dependencies
uv sync
```

## Running the Load Test

### Using uv (recommended)

```bash
# Run with default settings (uses environment variables from K8s deployment)
uv run load-test --host http://localhost:3001

# Quick smoke test
uv run load-test \
  --host http://localhost:3001 \
  --users 10 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless

# Medium load test
uv run load-test \
  --host http://localhost:3001 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless

# With web UI (no --headless flag)
uv run load-test --host http://localhost:3001
# Then open http://localhost:8089
```

### Environment Variables

The load test uses these environment variables (set automatically in K8s):

- `API_KEY_ENDPOINT` - Endpoint to create API keys (default: `/ai/admin/api-keys`)
- `TEST_DATA_FILE` - Path to test data file (default: `/test_data/batch_input_medium.jsonl`)
- `BASIC_AUTH_USERNAME` - Username for Basic Auth (used to create API key)
- `BASIC_AUTH_PASSWORD` - Password for Basic Auth (used to create API key)
- `P95_THRESHOLD_MS` - P95 response time threshold for assertions (default: 1000)
- `ERROR_RATE_THRESHOLD` - Error rate threshold for assertions (default: 0.01)

### Test Data Files

Three test data files are included:

- `test_data/batch_input_small.jsonl` - 3 requests (quick tests)
- `test_data/batch_input_medium.jsonl` - 10 requests (realistic)
- `test_data/batch_input_large.jsonl` - 50 requests (stress)

To use a different file locally:

```bash
export TEST_DATA_FILE=test_data/batch_input_small.jsonl
uv run load-test --host http://localhost:3001
```

## Development

### Running Tests Locally

```bash
# Start the control-layer service locally first
# Then run the load test

uv run load-test \
  --host http://localhost:3001 \
  --users 1 \
  --spawn-rate 1 \
  --run-time 30s \
  --headless
```

### Modifying the Test

Edit `locustfile.py` to modify the test workflow. The current implementation follows this sequence:

**Before any users start:**
- One shared API key is created using Basic Auth (first user only)
- All subsequent users reuse this shared API key

**Each user workflow:**
1. Upload JSONL file (using shared API key)
2. Verify upload (metadata or content)
3. Create batch job
4. Poll for completion (exponential backoff)
5. Retrieve output file
6. Retrieve error file (if exists)

**IMPORTANT**: The API key creation endpoint defaults to `/admin/api/v1/users/current/api-keys`.

To use a different endpoint, set the environment variable:
```bash
export API_KEY_ENDPOINT="/your/custom/endpoint"
uv run load-test --host http://localhost:3001
```

The API key endpoint response must contain a `key` field.

## Kubernetes Deployment

This locustfile is deployed via the Helm chart in `/charts/locust/`. See the main repository README for deployment instructions.

The Dockerfile packages this project for containerized execution in Kubernetes.
