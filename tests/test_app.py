import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_assistant.db"
os.environ["OPENAI_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app.database.database import Base, SessionLocal, engine
from app.dependencies import get_current_embedding_provider
from app.main import app
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import EmbeddingProvider
from app.services.chunking_service import chunk_text
from app.services.retrieval_service import RetrievedChunk
from app.services.text_extraction_service import extract_text


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        lowered = text.lower()
        if "architecture" in lowered:
            return [1.0, 0.0, 0.0]
        if "recipe" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_current_embedding_provider] = (
        lambda: FakeEmbeddingProvider()
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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
    documents_response = client.get("/documents")

    assert chat_response.status_code == 401
    assert memories_response.status_code == 401
    assert documents_response.status_code == 401


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
        lambda message, history, memories, document_chunks: (
            "Stored that preference."
        ),
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

    def fake_ask_ai(message, history, memories, document_chunks):
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


def test_text_extraction_and_chunking_for_markdown():
    text, metadata = extract_text(
        file_bytes=b"# Title\n\nThis is markdown content.",
        filename="notes.md",
        content_type="text/markdown",
    )
    chunks = chunk_text(text, max_characters=12, overlap_characters=3)

    assert metadata["document_type"] == "md"
    assert "markdown content" in text
    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0


def test_document_upload_and_listing(client):
    token = register_and_login(client)

    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "notes.txt",
                b"Personal knowledge about project architecture.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200
    document = upload_response.json()
    assert document["original_filename"] == "notes.txt"
    assert document["processing_status"] == "completed"
    assert document["metadata"]["chunk_count"] == 1

    list_response = client.get("/documents", headers=auth_headers(token))

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_document_ownership_isolation(client):
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
    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(first_token),
        files={
            "file": (
                "private.txt",
                b"Private document content.",
                "text/plain",
            )
        },
    )
    document_id = upload_response.json()["id"]

    first_list = client.get("/documents", headers=auth_headers(first_token))
    second_list = client.get("/documents", headers=auth_headers(second_token))
    second_get = client.get(
        f"/documents/{document_id}",
        headers=auth_headers(second_token),
    )

    assert len(first_list.json()) == 1
    assert second_list.json() == []
    assert second_get.status_code == 404


def test_document_delete_cascades_chunks(client):
    token = register_and_login(client)
    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "delete-me.txt",
                b"Cascade chunk content.",
                "text/plain",
            )
        },
    )
    document_id = upload_response.json()["id"]

    db = SessionLocal()
    chunk_count_before_delete = db.query(DocumentChunk).count()
    db.close()

    delete_response = client.delete(
        f"/documents/{document_id}",
        headers=auth_headers(token),
    )
    get_response = client.get(
        f"/documents/{document_id}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200
    assert get_response.status_code == 404
    assert chunk_count_before_delete == 1

    db = SessionLocal()
    chunk_count_after_delete = db.query(DocumentChunk).count()
    db.close()
    assert chunk_count_after_delete == 0


def test_semantic_retrieval_returns_relevant_chunks(client):
    token = register_and_login(client)
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "architecture.txt",
                b"System architecture and database design notes.",
                "text/plain",
            )
        },
    )
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "recipe.txt",
                b"Recipe notes about soup and vegetables.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/documents/search",
        headers=auth_headers(token),
        json={
            "query": "architecture",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["document_name"] == "architecture.txt"
    assert "architecture" in results[0]["content"].lower()


def test_semantic_retrieval_is_scoped_to_user(client):
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
        "/documents/upload",
        headers=auth_headers(first_token),
        files={
            "file": (
                "private-architecture.txt",
                b"Private architecture notes.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/documents/search",
        headers=auth_headers(second_token),
        json={
            "query": "architecture",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_semantic_retrieval_empty_results(client):
    token = register_and_login(client)

    response = client.post(
        "/documents/search",
        headers=auth_headers(token),
        json={
            "query": "architecture",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_chat_includes_retrieved_document_context(monkeypatch, client):
    token = register_and_login(client)
    observed_document_chunks = []

    monkeypatch.setattr(
        "app.routers.chat.extract_memory",
        lambda message: '{"remember": false}',
    )
    monkeypatch.setattr(
        "app.routers.chat.retrieve_relevant_chunks",
        lambda db, user_id, query, embedding_provider: [
            RetrievedChunk(
                document_id=1,
                document_name="notes.txt",
                chunk_id=10,
                chunk_index=0,
                content="Relevant document context.",
                metadata={"source": "test"},
            )
        ],
    )

    def fake_ask_ai(message, history, memories, document_chunks):
        observed_document_chunks.extend(document_chunks)
        return "Used document context."

    monkeypatch.setattr("app.routers.chat.ask_ai", fake_ask_ai)

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "rag-test",
            "message": "Use my notes.",
        },
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Used document context."
    assert observed_document_chunks[0].document_name == "notes.txt"
