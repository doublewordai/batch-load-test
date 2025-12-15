"""
Generic Locust Load Test

This is a simple example locustfile.
Override this by providing your own locustfile via values.yaml
"""

from locust import HttpUser, task, between


class QuickTestUser(HttpUser):
    """
    Simple test user that makes basic HTTP requests
    """
    wait_time = between(1, 3)

    @task
    def index(self):
        """Make a simple GET request"""
        self.client.get("/")
