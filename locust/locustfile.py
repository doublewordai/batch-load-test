"""
Locust load testing for Batch API

This locustfile simulates a realistic user workflow:
1. Upload a JSONL batch input file (using shared API key)
2. Verify the upload
3. Create a batch job
4. Poll for batch completion
5. Retrieve output file
6. Retrieve error file (if exists)

Authentication: One shared API key is created at test start using Basic Auth.
All users share this API key for their requests.
"""

from locust import HttpUser, SequentialTaskSet, task, between, events
import os
import random
import time
import json
from io import BytesIO


class BatchWorkflow(SequentialTaskSet):
    """
    Sequential workflow simulating a single user's batch processing journey.
    Each task executes in order, modeling realistic user behavior.
    """

    def on_start(self):
        """Initialize workflow with state variables"""
        self.file_id = None
        self.batch_id = None
        self.output_file_id = None
        self.error_file_id = None
        self.test_data = self.load_test_data()

    def load_test_data(self):
        """Load JSONL test data from file"""
        # Support environment variable override for selecting test data size
        test_data_file = os.getenv('TEST_DATA_FILE', '/test_data/batch_input_medium.jsonl')

        # Fallback chain: try specified file -> try batch_input.jsonl -> use minimal data
        try:
            with open(test_data_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback to minimal test data
            return '{"custom_id": "req-1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "load-test", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100}}\n'


    @task
    def upload_file(self):
        """Step 1: Upload JSONL batch input file"""
        # Create file-like object from test data
        test_data_bytes = self.test_data.encode('utf-8') if isinstance(self.test_data, str) else self.test_data
        file_obj = BytesIO(test_data_bytes)

        # Debug: Print first 200 chars of test data
        print(f"[DEBUG] Uploading file with {len(test_data_bytes)} bytes, first 200 chars: {test_data_bytes[:200]}")

        # OpenAI's exact format: file as tuple (filename, file_object)
        files = {
            'file': ('batch_input.jsonl', file_obj)
        }

        # purpose as form data
        data = {
            'purpose': 'batch'
        }

        # Don't set Content-Type - let requests handle multipart/form-data
        print(f"[DEBUG] Posting to: {self.client.base_url}/ai/v1/files")

        with self.client.post(
            "/ai/v1/files",
            files=files,
            data=data,
            catch_response=True,
            name="/ai/v1/files [upload]"
        ) as response:
            print(f"[DEBUG] Upload response: status={response.status_code}")
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            print(f"[DEBUG] Response body: {response.text[:500]}")
            if 'allow' in response.headers:
                print(f"[DEBUG] Allowed methods: {response.headers['allow']}")
            if response.status_code in [200, 201]:
                try:
                    response_data = response.json()
                    self.file_id = response_data.get('id')
                    if not self.file_id:
                        response.failure(f"No file ID in response: {response.text}")
                    else:
                        response.success()
                except (json.JSONDecodeError, KeyError) as e:
                    response.failure(f"Failed to parse response: {e}. Raw response: {response.text}")
            else:
                response.failure(f"Upload failed: {response.status_code} - {response.text}")

    @task
    def verify_upload(self):
        """Step 2: Verify file was uploaded successfully"""
        if not self.file_id:
            self.interrupt()
            return

        # Randomly choose between metadata or content verification
        if random.random() < 0.5:
            # Get metadata
            with self.client.get(
                f"/ai/v1/files/{self.file_id}",
                name="/ai/v1/files/{file_id} [metadata]",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get file metadata: {response.status_code}")
        else:
            # Get content
            with self.client.get(
                f"/ai/v1/files/{self.file_id}/content",
                name="/ai/v1/files/{file_id}/content [verify]",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get file content: {response.status_code}")

    @task
    def create_batch(self):
        """Step 3: Create batch job"""
        if not self.file_id:
            self.interrupt()
            return

        payload = {
            "input_file_id": self.file_id,
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h",
            "metadata": {
                "test_run": "locust",
                "locust_user": str(id(self))
            }
        }

        with self.client.post(
            "/ai/v1/batches",
            json=payload,
            catch_response=True,
            name="/ai/v1/batches [create]"
        ) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.batch_id = data.get('id')
                    response.success()
                except (json.JSONDecodeError, KeyError) as e:
                    response.failure(f"Failed to parse batch response: {e}")
            else:
                response.failure(f"Batch creation failed: {response.status_code} - {response.text}")

    @task
    def poll_batch_status(self):
        """Step 4: Poll batch status until completion"""
        if not self.batch_id:
            self.interrupt()
            return

        max_polls = 60  # Maximum number of polls
        poll_interval = 2  # Start with 2 seconds

        for i in range(max_polls):
            with self.client.get(
                f"/ai/v1/batches/{self.batch_id}",
                catch_response=True,
                name="/ai/v1/batches/{batch_id} [poll]"
            ) as response:
                if response.status_code == 200:
                    try:
                        data = response.json()
                        status = data.get('status')

                        if status in ['completed', 'failed', 'cancelled', 'expired']:
                            # Batch finished
                            self.output_file_id = data.get('output_file_id')
                            self.error_file_id = data.get('error_file_id')
                            response.success()
                            return
                        elif status in ['in_progress', 'validating', 'finalizing']:
                            # Still processing
                            response.success()
                        else:
                            response.failure(f"Unknown batch status: {status}")
                            return
                    except (json.JSONDecodeError, KeyError) as e:
                        response.failure(f"Failed to parse poll response: {e}")
                        return
                else:
                    response.failure(f"Poll failed: {response.status_code}")
                    return

            # Exponential backoff with cap
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 30)  # Cap at 30 seconds

        # Reached max polls without completion
        print(f"Batch {self.batch_id} did not complete within {max_polls} polls")

    @task
    def retrieve_output(self):
        """Step 5: Download output file"""
        if not self.output_file_id:
            # No output file, skip
            return

        with self.client.get(
            f"/ai/v1/files/{self.output_file_id}/content",
            name="/ai/v1/files/{output_file_id}/content [output]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to retrieve output: {response.status_code}")

    @task
    def retrieve_errors(self):
        """Step 6: Download error file if exists"""
        if not self.error_file_id:
            # No error file, skip
            return

        with self.client.get(
            f"/ai/v1/files/{self.error_file_id}/content",
            name="/ai/v1/files/{error_file_id}/content [errors]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to retrieve errors: {response.status_code}")


class BatchUser(HttpUser):
    """
    Simulates a user performing batch operations.
    Uses Basic Auth to create API key, then uses API key for all requests.
    """
    tasks = [BatchWorkflow]
    wait_time = between(1, 3)  # Wait 1-3 seconds between workflows

    # Shared API key across all users (class variable)
    shared_api_key = None
    api_key_lock = None

    def on_start(self):
        """Set up authentication - create shared API key or use existing one"""
        username = os.getenv('BASIC_AUTH_USERNAME', 'admin')
        password = os.getenv('BASIC_AUTH_PASSWORD', 'password')

        # Set up Basic Auth initially
        self.client.auth = (username, password)

        # Set headers
        self.client.headers.update({
            'User-Agent': 'Locust-LoadTest/1.0'
        })

        # Create or retrieve shared API key
        if BatchUser.shared_api_key is None:
            # Only the first user creates the API key
            self._create_shared_api_key()
        else:
            # Other users just use the existing key
            print(f"[DEBUG] Using existing shared API key")
            self.client.headers.update({
                'Authorization': f'Bearer {BatchUser.shared_api_key}'
            })
            self.client.auth = None

    def _create_shared_api_key(self):
        """Create a single shared API key for all users"""
        api_key_endpoint = os.getenv('API_KEY_ENDPOINT', '/admin/api/v1/users/current/api-keys')

        payload = {
            "burst_size": 0,
            "description": "load test",
            "name": "load-test",
            "purpose": "platform",
            "requests_per_second": 0
        }

        print(f"[DEBUG] Creating shared API key at {api_key_endpoint}")

        response = self.client.post(
            api_key_endpoint,
            json=payload,
            name="/admin/api-keys [create-shared]"
        )

        if response.status_code in [200, 201]:
            try:
                response_data = response.json()
                BatchUser.shared_api_key = response_data.get('key')

                if BatchUser.shared_api_key:
                    print(f"[DEBUG] Created shared API key: {BatchUser.shared_api_key[:20]}...")
                    # Switch to Bearer token
                    self.client.headers.update({
                        'Authorization': f'Bearer {BatchUser.shared_api_key}'
                    })
                    self.client.auth = None
                else:
                    print(f"[ERROR] No API key in response: {response.text}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[ERROR] Failed to parse API key response: {e}")
        else:
            print(f"[ERROR] API key creation failed: {response.status_code} - {response.text}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Event handler for test start"""
    print("\n" + "=" * 60)
    print("Starting Batch API Load Test")
    print("=" * 60)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users if hasattr(environment.parsed_options, 'num_users') else 'N/A'}")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Event handler for test stop - export metrics"""
    print("\n" + "=" * 60)
    print("Load Test Complete")
    print("=" * 60)

    stats = environment.stats

    # Print summary
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio:.2%}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"P50 Response Time: {stats.total.get_response_time_percentile(0.5):.2f}ms")
    print(f"P95 Response Time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 Response Time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print("=" * 60 + "\n")

    # Export detailed metrics as JSON
    try:
        metrics = {
            "summary": {
                "total_requests": stats.total.num_requests,
                "total_failures": stats.total.num_failures,
                "failure_rate": stats.total.fail_ratio,
                "avg_response_time_ms": stats.total.avg_response_time,
                "min_response_time_ms": stats.total.min_response_time,
                "max_response_time_ms": stats.total.max_response_time,
                "p50_ms": stats.total.get_response_time_percentile(0.5),
                "p95_ms": stats.total.get_response_time_percentile(0.95),
                "p99_ms": stats.total.get_response_time_percentile(0.99),
                "requests_per_second": stats.total.total_rps
            },
            "endpoints": {}
        }

        for name, stat in stats.entries.items():
            if name and name != "Aggregated":
                metrics["endpoints"][name] = {
                    "requests": stat.num_requests,
                    "failures": stat.num_failures,
                    "avg_response_time_ms": stat.avg_response_time,
                    "p95_ms": stat.get_response_time_percentile(0.95)
                }

        # Write to file
        with open('/results/metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)

        print("Metrics exported to /results/metrics.json")
    except Exception as e:
        print(f"Failed to export metrics: {e}")

    # Check performance assertions
    p95_threshold_ms = float(os.getenv('P95_THRESHOLD_MS', '1000'))
    error_rate_threshold = float(os.getenv('ERROR_RATE_THRESHOLD', '0.01'))

    failures = []

    p95 = stats.total.get_response_time_percentile(0.95)
    if p95 > p95_threshold_ms:
        failures.append(f"P95 response time {p95:.2f}ms exceeds threshold {p95_threshold_ms}ms")

    error_rate = stats.total.fail_ratio
    if error_rate > error_rate_threshold:
        failures.append(f"Error rate {error_rate:.2%} exceeds threshold {error_rate_threshold:.2%}")

    if failures:
        print("\n" + "!" * 60)
        print("PERFORMANCE ASSERTION FAILURES")
        print("!" * 60)
        for failure in failures:
            print(f"  ❌ {failure}")
        print("!" * 60 + "\n")
        # Note: Not exiting with error code to allow result collection
    else:
        print("\n" + "✓" * 60)
        print("ALL PERFORMANCE ASSERTIONS PASSED")
        print("✓" * 60 + "\n")
