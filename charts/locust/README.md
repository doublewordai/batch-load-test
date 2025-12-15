# Locust Load Testing Helm Chart

A generic, reusable Helm chart for deploying Locust load tests.

## Overview

This chart provides a flexible load testing framework for any HTTP API. It's designed as a **generic abstraction** - you provide your own locustfile and test data at deployment time.

### Key Design Principles

- **Generic by default**: Chart includes minimal example locustfile
- **Bring your own tests**: Supply custom locustfile via values
- **Flexible configuration**: Multiple test profiles and modes
- **Production-ready**: Supports both one-time Jobs and persistent Deployments

## Features

- ✅ **Generic & Reusable** - Not tied to any specific API
- ✅ **Flexible locustfile** - Provide inline or as file
- ✅ **Optional test data** - ConfigMap injection when needed
- ✅ **Multiple test profiles** - smoke, load, stress, soak
- ✅ **Authentication support** - Basic Auth via secrets
- ✅ **Performance assertions** - P95, error rate thresholds
- ✅ **Two modes** - Job (one-time) or Deployment (persistent UI)
- ✅ **Automatic results** - CSV, HTML, JSON export

## Installation

### Quick Start (Generic Example)

The chart includes a minimal example locustfile that makes simple GET requests:

```bash
helm install locust ./charts/locust \
  --set loadTest.host=https://example.com
```

### With Custom Locustfile

Provide your own locustfile inline:

```bash
helm install locust ./charts/locust \
  --set loadTest.host=http://my-api:8080 \
  --set-string locustfile.inline="$(cat my-locustfile.py)"
```

### Via Helmfile (Recommended)

**Best Practice**: Keep your locustfile as a `.py` file and inject it via helmfile's `set` directive:

```yaml
# values/my-load-test.yaml
loadTest:
  host: "http://my-api:8080"
  profile: load
```

```python
# locust/my-locustfile.py
from locust import HttpUser, task

class MyTestUser(HttpUser):
    @task
    def my_endpoint(self):
        self.client.get("/api/endpoint")
```

Reference in helmfile with file injection:

```yaml
- name: locust
  chart: ./charts/locust
  values:
    - values/my-load-test.yaml
  set:
    - name: locustfile.inline
      file: locust/my-locustfile.py
    - name: testData.inline
      file: locust/test_data/my-data.jsonl  # Optional
```

This keeps your locustfile in proper Python format with syntax highlighting and linting.

## Configuration

### Test Modes

**Job Mode** (one-time test run):
```yaml
mode: job
```

**Deployment Mode** (persistent web UI):
```yaml
mode: deployment
```

### Test Profiles

Pre-configured test profiles in `values.yaml`:

| Profile | Users | Spawn Rate | Duration | Purpose |
|---------|-------|------------|----------|---------|
| smoke   | 10    | 5          | 2m       | Quick validation |
| load    | 100   | 10         | 5m       | Normal load |
| stress  | 500   | 50         | 10m      | Stress testing |
| soak    | 100   | 10         | 30m      | Sustained load |

Select a profile:

```yaml
loadTest:
  profile: load
```

### Custom Load Parameters

Override profile settings:

```yaml
loadTest:
  users: 200
  spawnRate: 20
  runTime: "10m"
```

### Authentication

Use existing secret from control-layer:

```yaml
auth:
  existingSecret: control-layer-secret
  existingSecretUsernameKey: BASIC_AUTH_USERNAME
  existingSecretPasswordKey: BASIC_AUTH_PASSWORD
```

Or create new credentials:

```yaml
auth:
  existingSecret: ""
  username: "testuser"
  password: "testpass"
```

### Providing Locustfile

Four options to provide your locustfile:

**1. File injection via Helmfile (recommended)**

Keep your locustfile as a `.py` file and inject via helmfile's `set` directive:

```yaml
# helmfile.yaml
- name: locust
  chart: ./charts/locust
  set:
    - name: locustfile.inline
      file: locust/my-locustfile.py
```

This is the cleanest approach - your Python file stays as Python with proper syntax highlighting.

**2. Inline via --set-string (for helm CLI)**

```bash
helm install locust ./charts/locust \
  --set-string locustfile.inline="$(cat my-locustfile.py)"
```

**3. From file in chart**

Add your file to `charts/locust/files/my-locust.py`, then:

```yaml
locustfile:
  file: "my-locust.py"
```

**4. Default (generic example)**

Leave both empty to use the built-in example:

```yaml
locustfile:
  inline: ""
  file: ""
```

### Providing Test Data (Optional)

If your locustfile needs external test data:

**1. Multiple files via Helmfile (recommended):**

```yaml
# helmfile.yaml
set:
  - name: testData.files.small\.jsonl
    file: locust/test_data/small.jsonl
  - name: testData.files.medium\.jsonl
    file: locust/test_data/medium.jsonl
  - name: testData.files.large\.jsonl
    file: locust/test_data/large.jsonl
```

Files are mounted at `/test_data/{filename}`. In your locustfile:
```python
with open('/test_data/small.jsonl', 'r') as f:
    data = f.read()
```

**2. Single file via Helmfile:**

```yaml
# helmfile.yaml
set:
  - name: testData.inline
    file: locust/test_data/my-data.jsonl
```

Mounted at `/test_data/batch_input.jsonl`.

**3. Inline in values:**

```yaml
testData:
  inline: |
    {"request": 1, "data": "example"}
    {"request": 2, "data": "another"}
```

**4. From file in chart:**

```yaml
testData:
  file: "my-test-data.jsonl"
```

### Performance Assertions

Configure performance thresholds:

```yaml
assertions:
  p95ThresholdMs: 1000  # P95 response time must be < 1000ms
  errorRateThreshold: 0.01  # Error rate must be < 1%
```

## Usage

### Running Load Tests

**Via Helmfile:**

```bash
# Deploy entire stack including load test
helmfile apply

# Check job status
kubectl get jobs -n <namespace>

# View logs
kubectl logs job/locust-locust -n <namespace>
```

**Via Helm:**

```bash
# Install chart
helm install locust ./charts/locust

# Upgrade with different profile
helm upgrade locust ./charts/locust --set loadTest.profile=stress

# Uninstall
helm uninstall locust
```

### Collecting Results

```bash
# Wait for job to complete
kubectl wait --for=condition=complete job/locust-locust -n <namespace> --timeout=600s

# Get pod name
POD=$(kubectl get pod -l app.kubernetes.io/name=locust -n <namespace> -o jsonpath='{.items[0].metadata.name}')

# Copy results
kubectl cp <namespace>/${POD}:/results ./results/

# View results
ls -la results/
# - locust_stats.csv - Per-endpoint statistics
# - locust_stats_history.csv - Time-series data
# - locust_failures.csv - All failures
# - report.html - Interactive HTML report
# - metrics.json - JSON metrics summary
```

### Using Web UI (Deployment Mode)

```bash
# Deploy in deployment mode
helm install locust ./charts/locust --set mode=deployment

# Port forward to access UI
kubectl port-forward svc/locust-locust 8089:8089 -n <namespace>

# Open browser
open http://localhost:8089
```

## Examples

### Example 1: Simple API Test

Test a simple REST API:

```yaml
# values/simple-api-test.yaml
loadTest:
  host: "https://api.example.com"
  users: 50
  spawnRate: 5
  runTime: "5m"

locustfile:
  inline: |
    from locust import HttpUser, task, between

    class APIUser(HttpUser):
        wait_time = between(1, 3)

        @task(3)
        def get_users(self):
            self.client.get("/api/users")

        @task(1)
        def get_posts(self):
            self.client.get("/api/posts")
```

Deploy:
```bash
helm install api-test ./charts/locust -f values/simple-api-test.yaml
```

### Example 2: Batch API Load Test

This repository includes a complete batch API load test example:

**Files:**
- `locust/locustfile.py` - Sequential workflow (upload → verify → create batch → poll → retrieve)
- `locust/test_data/batch_input_small.jsonl` - 3 requests (quick tests)
- `locust/test_data/batch_input_medium.jsonl` - 10 requests (realistic)
- `locust/test_data/batch_input_large.jsonl` - 50 requests (stress)
- `values/locust-batch-test.yaml` - Configuration (host, auth, profile)

**Deployment:**
The helmfile injects the locustfile and all test data files:

```yaml
# helmfile.yaml excerpt
- name: locust
  values:
    - values/locust-batch-test.yaml
  set:
    - name: locustfile.inline
      file: locust/locustfile.py
    - name: testData.files.batch_input_small\.jsonl
      file: locust/test_data/batch_input_small.jsonl
    - name: testData.files.batch_input_medium\.jsonl
      file: locust/test_data/batch_input_medium.jsonl
    - name: testData.files.batch_input_large\.jsonl
      file: locust/test_data/batch_input_large.jsonl
```

All three test data files are mounted in `/test_data/`. The locustfile uses `batch_input_medium.jsonl` by default.

**To use a different file**, set `testData.selectedFile`:

```yaml
# locust-batch-test.yaml
testData:
  selectedFile: "batch_input_large.jsonl"  # Use large dataset for stress testing
```

Or override for different test profiles:

```bash
# Smoke test with small dataset
helm upgrade locust ./charts/locust \
  --reuse-values \
  --set loadTest.profile=smoke \
  --set testData.selectedFile=batch_input_small.jsonl

# Stress test with large dataset
helm upgrade locust ./charts/locust \
  --reuse-values \
  --set loadTest.profile=stress \
  --set testData.selectedFile=batch_input_large.jsonl
```

Deploy via helmfile:
```bash
helmfile apply
```

### Example 3: Authenticated API

Test API requiring authentication:

```yaml
loadTest:
  host: "https://secure-api.example.com"

auth:
  username: "testuser"
  password: "supersecret"

locustfile:
  inline: |
    from locust import HttpUser, task
    import os

    class SecureAPIUser(HttpUser):
        def on_start(self):
            # Basic Auth already set by chart
            pass

        @task
        def protected_endpoint(self):
            self.client.get("/api/protected")
```

### Example 4: Multiple Test Data Files

Use different test data files based on test profiles:

**Files:**
```python
# locust/multi-data-test.py
from locust import HttpUser, task
import json
import os

class DataDrivenUser(HttpUser):
    def on_start(self):
        # Load the selected test data file
        data_file = os.getenv('TEST_DATA_FILE', '/test_data/users.jsonl')
        with open(data_file, 'r') as f:
            self.test_data = [json.loads(line) for line in f]

    @task
    def api_call(self):
        import random
        data = random.choice(self.test_data)
        self.client.post("/api/action", json=data)
```

```jsonl
# locust/test_data/users_small.jsonl (10 users)
{"user_id": 1, "action": "login"}
{"user_id": 2, "action": "browse"}
...
```

```jsonl
# locust/test_data/users_large.jsonl (1000 users)
...
```

**Helmfile:**
```yaml
- name: multi-data-test
  chart: ./charts/locust
  values:
    - loadTest:
        host: "http://data-api:8080"
        profile: load
    - testData:
        selectedFile: "users_large.jsonl"  # Choose which dataset
  set:
    - name: locustfile.inline
      file: locust/multi-data-test.py
    - name: testData.files.users_small\.jsonl
      file: locust/test_data/users_small.jsonl
    - name: testData.files.users_large\.jsonl
      file: locust/test_data/users_large.jsonl
```

Now you can easily switch between datasets without changing your locustfile!

## Troubleshooting

### Job Never Completes

Check pod logs for errors:

```bash
kubectl logs -l app.kubernetes.io/name=locust -n <namespace>
```

Verify control-layer is accessible:

```bash
kubectl exec -it <pod-name> -n <namespace> -- curl http://control-layer:3001/health
```

### Authentication Failures

Verify secret exists and has correct keys:

```bash
kubectl get secret control-layer-secret -n <namespace> -o yaml
```

Check secret contains required keys:
- `BASIC_AUTH_USERNAME`
- `BASIC_AUTH_PASSWORD`

### High Error Rates

1. Check control-layer logs: `kubectl logs deployment/control-layer -n <namespace>`
2. Verify MockAI is running: `kubectl get pods -n <namespace>`
3. Reduce load: `--set loadTest.users=50`

### Out of Memory

Increase resources:

```yaml
resources:
  limits:
    memory: 4Gi
  requests:
    memory: 1Gi
```

## Architecture

### File Structure

```
locust/
├── locustfile.py - Sequential workflow implementation
├── Dockerfile - Container image
├── requirements.txt - Python dependencies
└── test_data/ - JSONL test files
    ├── batch_input_small.jsonl
    ├── batch_input_medium.jsonl
    └── batch_input_large.jsonl

charts/locust/
├── Chart.yaml
├── values.yaml
├── files/ - Chart-included files
│   ├── locustfile.py
│   └── *.jsonl
└── templates/
    ├── _helpers.tpl
    ├── job.yaml
    ├── configmap-locustfile.yaml
    ├── configmap-testdata.yaml
    ├── secret.yaml
    └── service.yaml
```

### Workflow Details

Each Locust user executes this sequential workflow:

1. **Upload** - Multipart/form-data file upload with JSONL content
2. **Verify** - Random choice between metadata or content check
3. **Create Batch** - JSON payload with input_file_id reference
4. **Poll** - Exponential backoff (2s → 30s max) until completion
5. **Retrieve** - Download output and error files if available

### Metrics Exported

- Total requests/failures
- Average/min/max response times
- P50/P95/P99 percentiles
- Requests per second
- Per-endpoint statistics

## Performance Targets

Default assertions:

- **P95 Response Time**: < 1000ms
- **Error Rate**: < 1%

Tests fail if thresholds are exceeded (visible in logs, but Job still succeeds to allow result collection).

## Dependencies

This chart depends on:

1. **control-layer** - Main API service
2. **db-init** - Database initialization
3. **openai-mock** - Mock inference endpoint

Helmfile ensures proper deployment order via `needs` directive.

## Values Reference

See [values.yaml](./values.yaml) for complete configuration options.

## License

MIT
