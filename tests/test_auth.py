"""Accounts, sessions, per-user isolation, and rate limiting."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.api import auth
from src.api.rate_limit import InMemoryRateLimiter, RedisRateLimiter, client_ip
from src.shared.config import settings
from tests.conftest import TEST_PASSWORD

ADA = {"email": "ada@example.com", "password": TEST_PASSWORD}


# --- Registration and sign-in --------------------------------------------------


def test_register_signs_in_with_a_hardened_cookie(anon_client):
    response = anon_client.post("/auth/register", json=ADA)
    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"
    cookie = response.headers["set-cookie"].lower()
    assert "session=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "password" not in response.text
    assert anon_client.get("/auth/me").json()["email"] == "ada@example.com"


def test_register_normalises_email_and_rejects_duplicates(anon_client):
    anon_client.post("/auth/register", json=ADA)
    anon_client.cookies.clear()
    response = anon_client.post(
        "/auth/register", json={"email": "  ADA@Example.com ", "password": TEST_PASSWORD}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"email": "not-an-email", "password": TEST_PASSWORD},
        {"email": "a@b", "password": TEST_PASSWORD},
        {"email": "x@example.com", "password": "short"},
        {"email": "x@example.com", "password": "é" * 37},  # 74 bytes > bcrypt's 72
    ],
)
def test_register_validates_input(anon_client, body):
    assert anon_client.post("/auth/register", json=body).status_code == 422


def test_login_and_logout(anon_client):
    anon_client.post("/auth/register", json=ADA)
    anon_client.post("/auth/logout")
    anon_client.cookies.clear()  # httpx keeps expired cookies until cleared
    assert anon_client.get("/auth/me").status_code == 401
    assert anon_client.post("/auth/login", json=ADA).status_code == 200
    assert anon_client.get("/auth/me").status_code == 200


def test_logout_expires_the_cookie(client):
    response = client.post("/auth/logout")
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_wrong_password_and_unknown_email_get_the_same_answer(anon_client):
    anon_client.post("/auth/register", json=ADA)
    anon_client.cookies.clear()
    wrong = anon_client.post("/auth/login", json={**ADA, "password": "wrong password!"})
    unknown = anon_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Incorrect email or password."}


def test_password_hashes_are_salted_and_verifiable():
    first, second = auth.hash_password("pw-123456"), auth.hash_password("pw-123456")
    assert first != second
    assert auth.verify_password("pw-123456", first)
    assert not auth.verify_password("other", first)
    assert not auth.verify_password("pw-123456", "not-a-hash")


# --- Tokens ----------------------------------------------------------------------


def test_protected_routes_require_sign_in(anon_client):
    for method, path in [
        ("get", "/tasks"),
        ("post", "/tasks"),
        ("get", "/tasks/x"),
        ("get", "/tasks/x/events"),
        ("post", "/tasks/x/cancel"),
        ("get", "/auth/me"),
    ]:
        assert getattr(anon_client, method)(path).status_code == 401, path


def test_tampered_and_expired_tokens_are_rejected(anon_client, monkeypatch):
    user_id = anon_client.post("/auth/register", json=ADA).json()["id"]
    anon_client.cookies.clear()
    good = auth.create_token(user_id)
    expired = auth.create_token(user_id, now=datetime.now(timezone.utc) - timedelta(days=2))
    for token, expected in [(good, 200), (good[:-2] + "xx", 401), (expired, 401)]:
        response = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == expected


def test_token_for_deleted_user_is_rejected(anon_client):
    token = auth.create_token("ghost-user-id")
    response = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_production_requires_a_configured_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "")
    monkeypatch.setattr(settings, "env", "production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        auth.signing_key()


def test_development_without_secret_uses_a_stable_random_key(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "")
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(auth, "_dev_secret", None)
    key = auth.signing_key()
    assert len(key) >= 32 and auth.signing_key() == key


# --- Isolation -------------------------------------------------------------------


def test_users_cannot_see_or_touch_each_others_runs(client):
    task_id = client.post("/tasks", json={"task": "Ada's private research"}).json()["id"]
    client.cookies.clear()
    client.post("/auth/register", json={"email": "bob@example.com", "password": TEST_PASSWORD})

    assert client.get("/tasks").json() == []
    assert client.get(f"/tasks/{task_id}").status_code == 404
    assert client.get(f"/tasks/{task_id}/events").status_code == 404
    assert client.post(f"/tasks/{task_id}/cancel").status_code == 404

    client.cookies.clear()
    client.post("/auth/login", json=ADA)
    assert client.get(f"/tasks/{task_id}").status_code == 200


# --- Rate limiting -----------------------------------------------------------------


def test_sign_in_attempts_are_rate_limited(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 2)
    bad = {"email": "nobody@example.com", "password": TEST_PASSWORD}
    codes = [anon_client.post("/auth/login", json=bad).status_code for _ in range(3)]
    assert codes == [401, 401, 429]


def test_task_creation_is_rate_limited_per_user(client, monkeypatch):
    monkeypatch.setattr(settings, "task_rate_limit_per_minute", 1)
    assert client.post("/tasks", json={"task": "one"}).status_code == 201
    response = client.post("/tasks", json={"task": "two"})
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_in_memory_limiter_resets_each_minute():
    clock = {"now": 120.0}
    limiter = InMemoryRateLimiter(clock=lambda: clock["now"])
    assert asyncio.run(limiter.hit("k"))[0] == 1
    assert asyncio.run(limiter.hit("k"))[0] == 2
    clock["now"] = 185.0
    count, retry_after = asyncio.run(limiter.hit("k"))
    assert count == 1 and 0 < retry_after <= 61


def test_redis_limiter_counts_and_expires_keys():
    class FakeRedis:
        def __init__(self):
            self.counts, self.expiry = {}, {}

        async def incr(self, key):
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        async def expire(self, key, seconds):
            self.expiry[key] = seconds

    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, clock=lambda: 60.0)
    assert [asyncio.run(limiter.hit("k"))[0] for _ in range(2)] == [1, 2]
    assert redis.expiry == {"ratelimit:k:1": 120}


def test_client_ip_trusts_forwarded_header_only_when_configured(monkeypatch):
    class FakeRequest:
        headers = {"x-forwarded-for": "203.0.113.9, 10.0.0.2"}
        client = type("Client", (), {"host": "10.0.0.2"})()

    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    assert client_ip(FakeRequest()) == "10.0.0.2"
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert client_ip(FakeRequest()) == "203.0.113.9"
