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


def test_memory_creation_and_retrieval(client):
    create_response = client.post(
        "/memories",
        json={
            "user_id": 1,
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()["key"] == "editor"

    list_response = client.get("/memories/1")

    assert list_response.status_code == 200
    memories = list_response.json()
    assert len(memories) == 1
    assert memories[0]["value"] == "VS Code"


def test_chat_flow_persists_messages_and_memory(monkeypatch, client):
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
        json={
            "conversation_id": "test-conversation",
            "user_id": 1,
            "message": "I prefer Python.",
        },
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Stored that preference."

    memories_response = client.get("/memories/1")
    memories = memories_response.json()

    assert len(memories) == 1
    assert memories[0]["key"] == "language"
