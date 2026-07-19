import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_assistant.db"
os.environ["OPENAI_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app.database.database import Base, SessionLocal, engine
from app.dependencies import (
    get_chat_orchestrator,
    get_current_embedding_provider,
    get_current_model_provider,
    get_model_router,
)
from app.main import app
from app.models.document_chunk import DocumentChunk
from app.providers.model_provider import ModelProvider, ProviderAvailabilityError
from app.providers.model_router import ModelRouter
from app.orchestrators.chat_orchestrator import ChatOrchestrator
from app.services.embedding_service import EmbeddingProvider
from app.services.embedding_backfill_service import backfill_missing_chunk_embeddings
from app.services.chunking_service import chunk_text
from app.services.retrieval_service import RetrievedChunk
from app.services.text_extraction_service import extract_text
from app.agents.planner_agent import PlannerAgent
from app.agents.types import Intent, Plan


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        lowered = text.lower()
        if "architecture" in lowered:
            return [1.0, 0.0, 0.0]
        if "recipe" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


class FakeModelProvider(ModelProvider):
    provider_name = "fake"
    generation_model = "fake-chat"
    embedding_model = "fake-embedding"

    def __init__(self):
        self.last_messages = []

    def generate(self, messages: list[dict]) -> str:
        self.last_messages = messages
        return "Fake model response."

    def generate_structured(
        self,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        return '{"ok": true}'

    def embed_text(self, text: str) -> list[float]:
        return FakeEmbeddingProvider().embed_text(text)


class FakeProvider(FakeModelProvider):
    def __init__(
        self,
        provider_name: str,
        generation_model: str,
        configured: bool = True,
        should_fail: bool = False,
        response: str | None = None,
    ):
        self._provider_name = provider_name
        self._generation_model = generation_model
        self._configured = configured
        self.should_fail = should_fail
        self.response = response or f"{provider_name} response"
        self.last_messages = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def generation_model(self) -> str:
        return self._generation_model

    @property
    def is_configured(self) -> bool:
        return self._configured

    def generate(self, messages: list[dict]) -> str:
        if self.should_fail:
            raise ProviderAvailabilityError(f"{self.provider_name} unavailable")
        self.last_messages = messages
        return self.response


def fake_model_router(
    providers: list[ModelProvider] | None = None,
    collaboration_enabled: bool = False,
) -> ModelRouter:
    configured_providers = providers or [FakeModelProvider()]
    return ModelRouter(
        providers=configured_providers,
        default_provider_name=configured_providers[0].provider_name,
        collaboration_enabled=collaboration_enabled,
    )


def override_model_provider(provider: ModelProvider) -> None:
    app.dependency_overrides[get_current_model_provider] = lambda: provider
    app.dependency_overrides[get_model_router] = (
        lambda: fake_model_router(providers=[provider])
    )


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
    app.dependency_overrides[get_current_model_provider] = (
        lambda: FakeModelProvider()
    )
    app.dependency_overrides[get_model_router] = lambda: fake_model_router()
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


def test_planner_routing():
    planner = PlannerAgent()

    assert planner.plan("hello there").intent == Intent.GENERAL_CHAT
    assert planner.plan("what do you remember about my editor").intent == (
        Intent.MEMORY_LOOKUP
    )
    assert planner.plan("search my documents").intent == Intent.KNOWLEDGE_SEARCH
    assert planner.plan("use my notes and preferences").intent == (
        Intent.COMBINED_CONTEXT
    )


def test_model_router_uses_openai_default():
    openai = FakeProvider("openai", "gpt-test")
    router = fake_model_router(providers=[openai])

    route = router.route(
        Plan(intent=Intent.GENERAL_CHAT, use_memory=True, use_knowledge=False),
        "Hello",
    )

    assert route.provider.provider_name == "openai"
    assert route.fallback_events == []


def test_model_router_routes_document_analysis_to_claude():
    openai = FakeProvider("openai", "gpt-test")
    claude = FakeProvider("anthropic", "claude-test")
    router = fake_model_router(providers=[openai, claude])

    route = router.route(
        Plan(intent=Intent.KNOWLEDGE_SEARCH, use_memory=False, use_knowledge=True),
        "Search my documents",
    )

    assert route.provider.provider_name == "anthropic"


def test_model_router_routes_multimodal_to_gemini():
    openai = FakeProvider("openai", "gpt-test")
    gemini = FakeProvider("gemini", "gemini-test")
    router = fake_model_router(providers=[openai, gemini])

    route = router.route(
        Plan(intent=Intent.GENERAL_CHAT, use_memory=True, use_knowledge=False),
        "Analyze this screenshot",
    )

    assert route.provider.provider_name == "gemini"


def test_model_router_routes_realtime_context_to_grok():
    openai = FakeProvider("openai", "gpt-test")
    grok = FakeProvider("xai", "grok-test")
    router = fake_model_router(providers=[openai, grok])

    route = router.route(
        Plan(intent=Intent.GENERAL_CHAT, use_memory=True, use_knowledge=False),
        "What is the latest social context?",
    )

    assert route.provider.provider_name == "xai"


def test_model_router_falls_back_when_preferred_unconfigured():
    openai = FakeProvider("openai", "gpt-test")
    claude = FakeProvider("anthropic", "claude-test", configured=False)
    router = fake_model_router(providers=[openai, claude])

    route = router.route(
        Plan(intent=Intent.KNOWLEDGE_SEARCH, use_memory=False, use_knowledge=True),
        "Search my documents",
    )

    assert route.provider.provider_name == "openai"
    assert route.fallback_events[0].from_provider == "anthropic"


def test_model_router_falls_back_on_provider_error():
    openai = FakeProvider("openai", "gpt-test")
    claude = FakeProvider("anthropic", "claude-test", should_fail=True)
    router = fake_model_router(providers=[openai, claude])
    route = router.route(
        Plan(intent=Intent.KNOWLEDGE_SEARCH, use_memory=False, use_knowledge=True),
        "Search my documents",
    )

    response = router.generate_with_fallback(
        route,
        [{"role": "user", "content": "hello"}],
    )

    assert response == "openai response"
    assert route.provider.provider_name == "openai"
    assert route.fallback_events[0].reason == "anthropic unavailable"


def test_model_router_collaboration_mode():
    openai = FakeProvider("openai", "gpt-test")
    claude = FakeProvider("anthropic", "claude-test")
    router = fake_model_router(
        providers=[openai, claude],
        collaboration_enabled=True,
    )

    route = router.route(
        Plan(intent=Intent.COMBINED_CONTEXT, use_memory=True, use_knowledge=True),
        "Use my documents and preferences",
    )
    analyses = router.collaborate(
        route,
        [{"role": "user", "content": "hello"}],
    )

    assert route.collaboration_mode is True
    assert analyses == ["anthropic response"]
    assert "anthropic" in route.providers_invoked


def test_chat_flow_persists_messages_and_memory(monkeypatch, client):
    token = register_and_login(client)

    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: (
            '{"remember": true, "category": "preference", '
            '"key": "language", "value": "Python"}'
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
    assert response.json()["response"] == "Fake model response."

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
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_histories.append(messages)
            return "ok"

    override_model_provider(ObservingModelProvider())

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
    assert {
        "role": "user",
        "content": "First user's message",
    } not in observed_histories[1]
    assert {
        "role": "user",
        "content": "Second user's message",
    } in observed_histories[1]


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
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )
    monkeypatch.setattr(
        "app.agents.knowledge_agent.retrieve_relevant_chunks",
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

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_document_chunks.extend(messages)
            return "Used document context."

    override_model_provider(ObservingModelProvider())

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
    assert any(
        "Relevant document context." in message["content"]
        for message in observed_document_chunks
    )


def test_orchestrator_memory_only_request(monkeypatch, client):
    token = register_and_login(client)
    observed_messages = []

    client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )
    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.extend(messages)
            return "memory-only"

    override_model_provider(ObservingModelProvider())

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "memory-only",
            "message": "What do you remember about my editor?",
        },
    )

    assert response.status_code == 200
    assert any("editor: VS Code" in item["content"] for item in observed_messages)


def test_orchestrator_knowledge_only_request(monkeypatch, client):
    token = register_and_login(client)
    observed_messages = []

    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.extend(messages)
            return "knowledge-only"

    override_model_provider(ObservingModelProvider())
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "architecture.txt",
                b"System architecture notes.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "knowledge-only",
            "message": "Search my documents for architecture",
        },
    )

    assert response.status_code == 200
    assert any(
        "System architecture notes" in item["content"]
        for item in observed_messages
    )


def test_orchestrator_combined_context_and_metadata(monkeypatch, client):
    token = register_and_login(client)
    orchestrator = ChatOrchestrator()

    app.dependency_overrides[get_chat_orchestrator] = lambda: orchestrator
    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )
    client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "architecture.txt",
                b"Architecture knowledge.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "combined",
            "message": "Use my documents and my editor preference",
        },
    )

    assert response.status_code == 200
    metadata = orchestrator.last_execution_metadata
    assert metadata is not None
    assert metadata.selected_intent == "combined_context"
    assert "PlannerAgent" in metadata.agents_invoked
    assert "EvaluatorAgent" in metadata.agents_invoked
    assert metadata.retrieval_count == 1
    assert metadata.provider == "fake"


def test_orchestrator_user_isolation(monkeypatch, client):
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
    observed_messages = []

    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.append(messages)
            return "ok"

    override_model_provider(ObservingModelProvider())
    client.post(
        "/memories",
        headers=auth_headers(first_token),
        json={
            "category": "preference",
            "key": "private",
            "value": "first-user-only",
        },
    )
    client.post(
        "/chat",
        headers=auth_headers(second_token),
        json={
            "conversation_id": "isolation",
            "message": "What do you remember about my private preference?",
        },
    )

    assert not any(
        "first-user-only" in item["content"]
        for item in observed_messages[0]
    )


def test_embedding_backfill_idempotency(client):
    token = register_and_login(client)
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "architecture.txt",
                b"Architecture content.",
                "text/plain",
            )
        },
    )

    db = SessionLocal()
    chunk = db.query(DocumentChunk).first()
    chunk.embedding = None
    db.commit()
    db.close()

    db = SessionLocal()
    first_result = backfill_missing_chunk_embeddings(
        db,
        embedding_provider=FakeEmbeddingProvider(),
    )
    second_result = backfill_missing_chunk_embeddings(
        db,
        embedding_provider=FakeEmbeddingProvider(),
    )
    db.close()

    assert first_result.updated_count == 1
    assert first_result.failed_count == 0
    assert second_result.updated_count == 0
    assert second_result.skipped_count == 1
