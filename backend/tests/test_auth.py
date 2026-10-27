import pytest
from fastapi import status


def test_register_success(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "StrongPassword999!", "full_name": "Test User"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "Test User"
    assert "hashed_password" not in data
    assert "id" in data


def test_register_duplicate_email(client):
    resp1 = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "Password123!"},
    )
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "Password123!"},
    )
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in resp2.json()["detail"]


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "loginuser@example.com", "password": "ValidPassword123!"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "ValidPassword123!"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpwd@example.com", "password": "CorrectPassword123!"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpwd@example.com", "password": "IncorrectPassword!"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in resp.json()["detail"]


def test_login_nonexistent_user(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword!"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "Password123!"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "Password123!"},
    )
    tokens = login_resp.json()

    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == status.HTTP_200_OK
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


def test_get_current_user_profile(client, auth_headers_user_a):
    resp = client.get("/api/v1/auth/me", headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["email"] == "user_a@example.com"
    assert data["is_active"] is True


def test_register_invalid_email_format(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "Password123!"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_protected_route_without_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
