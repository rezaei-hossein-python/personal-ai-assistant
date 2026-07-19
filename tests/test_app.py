import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_assistant.db"
os.environ["OPENAI_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app.database.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_application_startup(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Personal AI Assistant API is running"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def register_and_login(
    client,
    email: str = "user@example.com",
    name: str = "Test User",
    password: str = "correct-horse-battery-staple",
):
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "name": name,
            "password": password,
        },
    )
    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_registration_and_login(client):
    token = register_and_login(client)

    assert token


def test_login_rejects_invalid_password(client):
    client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "name": "Test User",
            "password": "right-password",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_unauthorized_access_is_rejected(client):
    chat_response = client.post(
        "/chat",
        json={
            "conversation_id": "test-conversation",
            "message": "Hello",
        },
    )
    memories_response = client.get("/memories")

    assert chat_response.status_code == 401
    assert memories_response.status_code == 401


def test_memory_creation_and_retrieval(client):
    token = register_and_login(client)

    create_response = client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()["key"] == "editor"

    list_response = client.get("/memories", headers=auth_headers(token))

    assert list_response.status_code == 200
    memories = list_response.json()
    assert len(memories) == 1
    assert memories[0]["value"] == "VS Code"


def test_chat_flow_persists_messages_and_memory(monkeypatch, client):
    token = register_and_login(client)

    monkeypatch.setattr(
        "app.routers.chat.extract_memory",
        lambda message: (
            '{"remember": true, "category": "preference", '
            '"key": "language", "value": "Python"}'
        ),
    )
    monkeypatch.setattr(
        "app.routers.chat.ask_ai",
        lambda message, history, memories: "Stored that preference.",
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "test-conversation",
            "message": "I prefer Python.",
        },
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Stored that preference."

    memories_response = client.get("/memories", headers=auth_headers(token))
    memories = memories_response.json()

    assert len(memories) == 1
    assert memories[0]["key"] == "language"


def test_memory_ownership_isolation(client):
    first_token = register_and_login(
        client,
        email="first@example.com",
        name="First User",
    )
    second_token = register_and_login(
        client,
        email="second@example.com",
        name="Second User",
    )

    client.post(
        "/memories",
        headers=auth_headers(first_token),
        json={
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )

    first_response = client.get("/memories", headers=auth_headers(first_token))
    second_response = client.get("/memories", headers=auth_headers(second_token))

    assert len(first_response.json()) == 1
    assert second_response.json() == []

    memory_id = first_response.json()[0]["id"]
    delete_response = client.delete(
        f"/memories/{memory_id}",
        headers=auth_headers(second_token),
    )

    assert delete_response.status_code == 404


def test_chat_history_isolated_for_same_conversation_id(monkeypatch, client):
    first_token = register_and_login(
        client,
        email="first@example.com",
        name="First User",
    )
    second_token = register_and_login(
        client,
        email="second@example.com",
        name="Second User",
    )
    observed_histories = []

    monkeypatch.setattr(
        "app.routers.chat.extract_memory",
        lambda message: '{"remember": false}',
    )

    def fake_ask_ai(message, history, memories):
        observed_histories.append(history)
        return "ok"

    monkeypatch.setattr("app.routers.chat.ask_ai", fake_ask_ai)

    client.post(
        "/chat",
        headers=auth_headers(first_token),
        json={
            "conversation_id": "shared-id",
            "message": "First user's message",
        },
    )
    response = client.post(
        "/chat",
        headers=auth_headers(second_token),
        json={
            "conversation_id": "shared-id",
            "message": "Second user's message",
        },
    )

    assert response.status_code == 200
    assert observed_histories[1] == [
        {
            "role": "user",
            "content": "Second user's message",
        }
    ]
