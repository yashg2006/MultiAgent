"""
Load test for the API (run against the Mock provider so it's free and fast).

Each simulated user registers once, then repeatedly submits a task and polls it
to completion, exercising the full auth + queue + pipeline + DB path.

    locust -f scripts/locustfile.py --host http://localhost:8080 \
        --headless -u 20 -r 5 -t 1m --csv docs/results/loadtest
"""

from __future__ import annotations

import time
import uuid

from locust import HttpUser, between, task

TASKS = [
    "Explain how TCP congestion control works.",
    "Compare REST and GraphQL for building web APIs.",
    "Summarize how a blockchain reaches consensus.",
    "Describe how an SSD differs from a hard disk.",
]


class ApiUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = f"load-{uuid.uuid4().hex[:12]}@example.com"
        self.client.post("/auth/register", json={"email": email, "password": "load-password-123"})

    @task
    def submit_and_poll(self) -> None:
        prompt = TASKS[int(time.time()) % len(TASKS)]
        created = self.client.post("/tasks", json={"task": prompt})
        if created.status_code != 201:
            return
        task_id = created.json()["id"]
        deadline = time.time() + 30
        while time.time() < deadline:
            response = self.client.get(f"/tasks/{task_id}", name="/tasks/{id}")
            if response.status_code == 200 and response.json()["status"] not in (
                "pending",
                "running",
            ):
                break
            time.sleep(1)
