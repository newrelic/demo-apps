from locust import HttpUser, task, between, constant_pacing
import os

# Configuration
TARGET_HOST = os.getenv("LOCUST_TARGET_HOST", "http://java-app:8080")


class NormalTrafficUser(HttpUser):
    """Scenario 1: Normal baseline traffic (1 req/sec to /health)"""
    wait_time = constant_pacing(1)  # 1 request per second

    @task
    def health_check(self):
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class CpuSpikeUser(HttpUser):
    """Scenario 2: CPU spike (burst of cpu-burn requests)"""
    wait_time = between(0.1, 0.5)  # Aggressive request rate

    @task
    def cpu_burn(self):
        with self.client.get("/api/cpu-burn", catch_response=True, timeout=10) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"CPU burn failed: {response.status_code}")


class MemoryPressureUser(HttpUser):
    """Scenario 3: Memory pressure (steady stream to memory-pressure)"""
    wait_time = constant_pacing(5)  # 1 request every 5 seconds

    @task
    def memory_pressure(self):
        with self.client.get("/api/memory-pressure", catch_response=True, timeout=10) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Memory pressure failed: {response.status_code}")


class LockContentionUser(HttpUser):
    """Scenario 4: Lock contention (few requests to trigger blocking)"""
    wait_time = constant_pacing(2)  # 1 request every 2 seconds

    @task
    def lock_contention(self):
        with self.client.get("/api/lock-contention", catch_response=True, timeout=15) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Lock contention failed: {response.status_code}")


class IoWaitUser(HttpUser):
    """Scenario 5: IO wait (occasional io-wait requests)"""
    wait_time = constant_pacing(3)  # 1 request every 3 seconds

    @task
    def io_wait(self):
        with self.client.get("/api/io-wait", catch_response=True, timeout=15) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"IO wait failed: {response.status_code}")
