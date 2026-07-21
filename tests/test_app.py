import os
from io import BytesIO

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_assistant.db"
os.environ["OPENAI_API_KEY"] = "test-key"

from fastapi.testclient import TestClient

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.config import Settings, settings
from app.database.database import Base, SessionLocal, engine
from app.dependencies import (
    get_chat_orchestrator,
    get_current_embedding_provider,
    get_current_model_provider,
    get_model_router,
)
from app.main import app
from app.models.conversation import Conversation
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.models.user import User
from app.providers.model_provider import ModelProvider, ProviderAvailabilityError
from app.providers.model_router import ModelRouter
from app.orchestrators.chat_orchestrator import ChatOrchestrator
from app.services.embedding_service import EmbeddingProvider
from app.services.embedding_backfill_service import backfill_missing_chunk_embeddings
from app.services.chunking_service import chunk_text
from app.services.retrieval_service import RetrievedChunk, VectorSearchUnavailableError
from app.services.text_extraction_service import extract_text
from app.agents.planner_agent import PlannerAgent
from app.agents.types import ActionRequest, Intent, Plan
from app.agents.action_agent import ActionAgent
from app.tools import ToolContext, ToolRegistry, build_default_tool_registry
from app.tools.internal_tools import INTERNAL_TOOLS


def make_docx_bytes(text: str) -> bytes:
    from docx import Document as DocxDocument

    buffer = BytesIO()
    document = DocxDocument()
    document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


def make_pdf_bytes(text: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


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


def test_ready_endpoint_checks_database(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["database"] == "ok"


def test_ready_endpoint_returns_503_when_database_unavailable(monkeypatch, client):
    def unavailable():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.routers.health.get_readiness_status", unavailable)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Application is not ready"


def test_settings_parse_allowed_origins_from_comma_string():
    configured = Settings(
        APP_ENV="test",
        DATABASE_URL="sqlite:///./test.db",
        OPENAI_API_KEY="test-key",
        ALLOWED_ORIGINS="http://localhost:5173,https://example.com",
    )

    assert configured.ALLOWED_ORIGINS == [
        "http://localhost:5173",
        "https://example.com",
    ]


def test_production_settings_require_secrets():
    configured = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql+psycopg2://user:pass@localhost/db",
        OPENAI_API_KEY="",
        JWT_SECRET_KEY="short",
        API_DOCS_ENABLED=False,
        ALLOWED_ORIGINS="https://example.com",
    )

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        configured.validate_for_startup()


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
    conversations_response = client.get("/conversations")

    assert chat_response.status_code == 401
    assert memories_response.status_code == 401
    assert documents_response.status_code == 401
    assert conversations_response.status_code == 401


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


def test_memory_deletion(client):
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
    memory_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/memories/{memory_id}",
        headers=auth_headers(token),
    )
    list_response = client.get("/memories", headers=auth_headers(token))

    assert delete_response.status_code == 200
    assert list_response.json() == []


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


def test_action_agent_selects_initial_tools():
    agent = ActionAgent()

    assert agent.select_actions(
        "Remember that my favorite programming language is Python."
    )[0].tool_name == "save_memory"
    assert agent.select_actions("What documents do I have?")[0].tool_name == (
        "list_documents"
    )
    assert agent.select_actions(
        "Search my documents for Nastaran's application."
    )[0].tool_name == "search_knowledge"
    assert agent.select_actions("What conversations do I have?")[0].tool_name == (
        "list_conversations"
    )
    assert agent.select_actions("Hello there.") == []


def test_tool_argument_validation(client):
    token = register_and_login(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        registry = build_default_tool_registry()
        result, execution = registry.execute(
            ToolContext(db, user.id, FakeEmbeddingProvider()),
            "save_memory",
            {
                "category": "preference",
                "key": "",
                "value": "Python",
            },
        )
    finally:
        db.close()

    assert result.status == "error"
    assert result.error["code"] == "invalid_arguments"
    assert execution.summary == "Tool arguments were invalid."


def test_tool_allowlist_blocks_unknown_tool(client):
    token = register_and_login(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        registry = ToolRegistry(INTERNAL_TOOLS, allowed_tools={"list_memories"})
        result, execution = registry.execute(
            ToolContext(db, user.id, FakeEmbeddingProvider()),
            "save_memory",
            {
                "category": "preference",
                "key": "language",
                "value": "Python",
            },
        )
    finally:
        db.close()

    assert result.status == "error"
    assert result.error["code"] == "tool_not_allowed"
    assert execution.name == "save_memory"


def test_tool_registry_execution_limit_is_strict():
    registry = build_default_tool_registry()

    assert registry.max_executions == 1


def test_orchestrator_enforces_tool_execution_limit(client):
    token = register_and_login(client)

    class TwoActionAgent(ActionAgent):
        def select_actions(self, message: str) -> list[ActionRequest]:
            return [
                ActionRequest(tool_name="list_memories", arguments={}),
                ActionRequest(tool_name="list_documents", arguments={}),
            ]

    app.dependency_overrides[get_chat_orchestrator] = (
        lambda: ChatOrchestrator(action_agent=TwoActionAgent())
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "execution-limit",
            "message": "Run two tools.",
        },
    )

    assert response.status_code == 200
    assert response.json()["metadata"]["actions"] == [
        {
            "tool_name": "list_memories",
            "status": "success",
            "summary": "Listed memories",
        },
        {
            "tool_name": "execution_limit",
            "status": "error",
            "summary": "Tool execution limit reached.",
        },
    ]


def test_tool_structured_error_for_missing_memory(client):
    token = register_and_login(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        registry = build_default_tool_registry()
        result, execution = registry.execute(
            ToolContext(db, user.id, FakeEmbeddingProvider()),
            "delete_memory",
            {
                "key": "missing_memory",
            },
        )
    finally:
        db.close()

    assert result.status == "error"
    assert result.error == {
        "code": "memory_not_found",
        "message": "Memory not found.",
    }
    assert execution.summary == "Memory not found."


def test_internal_memory_tools_are_user_scoped(client):
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

    db = SessionLocal()
    try:
        first_user = db.query(User).filter(User.email == "first@example.com").one()
        second_user = db.query(User).filter(User.email == "second@example.com").one()
        registry = build_default_tool_registry()
        first_result, _ = registry.execute(
            ToolContext(db, first_user.id, FakeEmbeddingProvider()),
            "list_memories",
            {},
        )
        second_result, _ = registry.execute(
            ToolContext(db, second_user.id, FakeEmbeddingProvider()),
            "list_memories",
            {},
        )
    finally:
        db.close()

    assert first_result.data["count"] == 1
    assert second_result.data["count"] == 0
    assert second_token


def test_internal_save_and_delete_memory_tools(client):
    token = register_and_login(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        registry = build_default_tool_registry()
        save_result, _ = registry.execute(
            ToolContext(db, user.id, FakeEmbeddingProvider()),
            "save_memory",
            {
                "category": "preference",
                "key": "favorite_language",
                "value": "Python",
            },
        )
        delete_result, _ = registry.execute(
            ToolContext(db, user.id, FakeEmbeddingProvider()),
            "delete_memory",
            {
                "key": "favorite_language",
            },
        )
        list_result, _ = registry.execute(
            ToolContext(db, user.id, FakeEmbeddingProvider()),
            "list_memories",
            {},
        )
    finally:
        db.close()

    assert save_result.status == "success"
    assert delete_result.status == "success"
    assert list_result.data["memories"] == []


def test_delete_memory_requires_explicit_intent_in_chat(client):
    token = register_and_login(client)
    client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "no-delete",
            "message": "What do you remember about my editor?",
        },
    )
    memories_response = client.get("/memories", headers=auth_headers(token))

    assert response.status_code == 200
    assert memories_response.json()[0]["key"] == "editor"
    assert response.json()["metadata"]["actions"] == []


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


def test_chat_flow_persists_messages_without_auto_memory(monkeypatch, client):
    token = register_and_login(client)

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

    assert memories == []


def test_chat_save_memory_tool_persists_memory(client):
    token = register_and_login(client)

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "save-memory-tool",
            "message": "Remember that my favorite programming language is Python.",
        },
    )
    memories_response = client.get("/memories", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == (
        "Saved to memory: favorite_programming_language is python."
    )
    assert body["metadata"]["actions"] == [
        {
            "tool_name": "save_memory",
            "status": "success",
            "summary": "Saved to memory",
        }
    ]
    assert memories_response.json()[0]["key"] == "favorite_programming_language"
    assert memories_response.json()[0]["value"] == "python"


def test_chat_list_documents_tool(client):
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

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "list-documents-tool",
            "message": "What documents do I have?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "architecture.txt" in body["response"]
    assert body["metadata"]["actions"][0] == {
        "tool_name": "list_documents",
        "status": "success",
        "summary": "Listed documents",
    }


def test_chat_search_knowledge_tool_preserves_rag_metadata(client):
    token = register_and_login(client)
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "nastaran.txt",
                b"Nastaran application notes.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "search-knowledge-tool",
            "message": "Search my documents for Nastaran's application.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["actions"][0] == {
        "tool_name": "search_knowledge",
        "status": "success",
        "summary": "Searched knowledge",
    }
    assert body["metadata"]["knowledge"]["enabled"] is True
    assert body["metadata"]["knowledge"]["retrieval_count"] == 1


def test_chat_list_conversations_tool_preserves_history(client):
    token = register_and_login(client)
    client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "history-before-list",
            "message": "Hello there.",
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "history-list-tool",
            "message": "What conversations do I have?",
        },
    )
    conversations_response = client.get("/conversations", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["actions"][0] == {
        "tool_name": "list_conversations",
        "status": "success",
        "summary": "Listed conversations",
    }
    assert len(conversations_response.json()) == 2


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


def test_conversation_message_orm_navigation(monkeypatch, client):
    token = register_and_login(client)

    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "orm-navigation",
            "message": "Persist this.",
        },
    )

    assert response.status_code == 200

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        conversation = db.query(Conversation).filter(
            Conversation.user_id == user.id,
            Conversation.conversation_id == "orm-navigation",
        ).one()

        assert conversation.user == user
        assert conversation in user.conversations
        assert [message.role for message in conversation.messages] == [
            "user",
            "assistant",
        ]
        assert conversation.messages[0].conversation == conversation
        assert conversation.messages[0] in user.messages
    finally:
        db.close()


def test_conversation_message_schema_constraints_exist(client):
    inspector = inspect(engine)

    conversation_unique_constraints = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("conversations")
    }
    message_foreign_keys = {
        (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("messages")
    }
    conversation_foreign_keys = {
        (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("conversations")
    }

    assert ("user_id", "conversation_id") in conversation_unique_constraints
    assert (("user_id",), "users", ("id",)) in conversation_foreign_keys
    assert (("user_id",), "users", ("id",)) in message_foreign_keys
    assert (
        ("user_id", "conversation_id"),
        "conversations",
        ("user_id", "conversation_id"),
    ) in message_foreign_keys


def test_conversation_message_database_constraints(client):
    token = register_and_login(client)

    client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "constraint-check",
            "message": "Create a valid conversation.",
        },
    )

    db = SessionLocal()
    try:
        db.execute(text("PRAGMA foreign_keys=ON"))
        first_user = db.query(User).filter(User.email == "user@example.com").one()
        second_user = User(
            email="second@example.com",
            name="Second User",
            hashed_password="hash",
        )
        db.add(second_user)
        db.commit()

        db.add(
            Conversation(
                conversation_id="constraint-check",
                user_id=first_user.id,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(
            Message(
                conversation_id="constraint-check",
                user_id=second_user.id,
                role="user",
                content="This should not attach to another user's conversation.",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_chat_creates_conversation_and_conversation_api_lists_messages(client):
    token = register_and_login(client)

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "history-v1",
            "message": "Show this in history.",
        },
    )
    list_response = client.get("/conversations", headers=auth_headers(token))
    detail_response = client.get(
        "/conversations/history-v1",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert list_response.status_code == 200
    conversations = list_response.json()
    assert len(conversations) == 1
    assert conversations[0]["conversation_id"] == "history-v1"
    assert conversations[0]["message_count"] == 2
    assert conversations[0]["first_user_message"] == "Show this in history."
    assert conversations[0]["updated_at"] is not None

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["conversation_id"] == "history-v1"
    assert [(message["role"], message["content"]) for message in detail["messages"]] == [
        ("user", "Show this in history."),
        ("assistant", "Fake model response."),
    ]
    assert all(message["created_at"] is not None for message in detail["messages"])


def test_conversation_api_is_user_scoped(client):
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
        "/chat",
        headers=auth_headers(first_token),
        json={
            "conversation_id": "private-history",
            "message": "First user only.",
        },
    )

    first_list = client.get("/conversations", headers=auth_headers(first_token))
    second_list = client.get("/conversations", headers=auth_headers(second_token))
    second_detail = client.get(
        "/conversations/private-history",
        headers=auth_headers(second_token),
    )
    second_delete = client.delete(
        "/conversations/private-history",
        headers=auth_headers(second_token),
    )

    assert [item["conversation_id"] for item in first_list.json()] == [
        "private-history"
    ]
    assert second_list.json() == []
    assert second_detail.status_code == 404
    assert second_delete.status_code == 404


def test_delete_conversation_removes_owned_messages(client):
    token = register_and_login(client)
    client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "delete-history",
            "message": "Delete me.",
        },
    )

    delete_response = client.delete(
        "/conversations/delete-history",
        headers=auth_headers(token),
    )
    detail_response = client.get(
        "/conversations/delete-history",
        headers=auth_headers(token),
    )
    list_response = client.get("/conversations", headers=auth_headers(token))

    db = SessionLocal()
    try:
        remaining_messages = db.query(Message).filter(
            Message.conversation_id == "delete-history"
        ).all()
    finally:
        db.close()

    assert delete_response.status_code == 200
    assert detail_response.status_code == 404
    assert list_response.json() == []
    assert remaining_messages == []


def test_continuing_existing_conversation_appends_messages(client):
    token = register_and_login(client)

    first_response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "continued-history",
            "message": "First turn.",
        },
    )
    second_response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "continued-history",
            "message": "Second turn.",
        },
    )
    detail_response = client.get(
        "/conversations/continued-history",
        headers=auth_headers(token),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert [(message["role"], message["content"]) for message in detail_response.json()["messages"]] == [
        ("user", "First turn."),
        ("assistant", "Fake model response."),
        ("user", "Second turn."),
        ("assistant", "Fake model response."),
    ]


def test_failed_assistant_generation_does_not_persist_assistant_message(client):
    token = register_and_login(client)

    class FailingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            raise RuntimeError("generation failed")

    override_model_provider(FailingModelProvider())

    with pytest.raises(RuntimeError, match="generation failed"):
        client.post(
            "/chat",
            headers=auth_headers(token),
            json={
                "conversation_id": "failed-generation",
                "message": "This generation fails.",
            },
        )

    db = SessionLocal()
    try:
        persisted_messages = (
            db.query(Message)
            .filter(Message.conversation_id == "failed-generation")
            .order_by(Message.id)
            .all()
        )
    finally:
        db.close()

    assert [(message.role, message.content) for message in persisted_messages] == [
        ("user", "This generation fails."),
    ]


def test_new_conversation_id_creates_separate_history(client):
    token = register_and_login(client)

    client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "first-new-chat",
            "message": "First chat.",
        },
    )
    client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "second-new-chat",
            "message": "Second chat.",
        },
    )

    list_response = client.get("/conversations", headers=auth_headers(token))
    conversation_ids = {
        conversation["conversation_id"] for conversation in list_response.json()
    }

    assert conversation_ids == {"first-new-chat", "second-new-chat"}


def test_conversation_history_persists_across_login_sessions(client):
    token = register_and_login(client)
    client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "relogin-history",
            "message": "Persist after logout.",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    new_token = login_response.json()["access_token"]
    list_response = client.get("/conversations", headers=auth_headers(new_token))
    detail_response = client.get(
        "/conversations/relogin-history",
        headers=auth_headers(new_token),
    )

    assert login_response.status_code == 200
    assert [item["conversation_id"] for item in list_response.json()] == [
        "relogin-history"
    ]
    assert detail_response.json()["messages"][0]["content"] == "Persist after logout."


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


def test_document_upload_sanitizes_unsafe_filename(client):
    token = register_and_login(client)

    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "../unsafe:name.txt",
                b"Personal knowledge about project architecture.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200
    assert upload_response.json()["original_filename"] == "unsafe_name.txt"


def test_document_upload_rejects_unsupported_extension(client):
    token = register_and_login(client)

    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "notes.exe",
                b"not a supported document",
                "application/octet-stream",
            )
        },
    )

    assert upload_response.status_code == 400
    assert upload_response.json()["detail"] == "Unsupported document type"


def test_document_upload_rejects_oversized_file(monkeypatch, client):
    token = register_and_login(client)
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 8)

    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "notes.txt",
                b"this file is too large",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 413
    assert upload_response.json()["detail"] == "Uploaded file is too large"


@pytest.mark.parametrize(
    ("filename", "content_factory", "content_type", "document_type"),
    [
        (
            "notes.txt",
            lambda: b"Personal knowledge about project architecture.",
            "text/plain",
            "txt",
        ),
        (
            "notes.md",
            lambda: b"# Architecture\n\nMarkdown knowledge about project architecture.",
            "text/markdown",
            "md",
        ),
        (
            "notes.docx",
            lambda: make_docx_bytes("DOCX knowledge about project architecture."),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        ),
        (
            "notes.pdf",
            lambda: make_pdf_bytes("PDF knowledge about project architecture."),
            "application/pdf",
            "pdf",
        ),
    ],
    ids=["txt", "markdown", "docx", "pdf"],
)
def test_authenticated_upload_ingests_supported_document_types(
    client,
    filename,
    content_factory,
    content_type,
    document_type,
):
    token = register_and_login(client)

    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                filename,
                content_factory(),
                content_type,
            )
        },
    )

    assert upload_response.status_code == 200
    document = upload_response.json()
    assert document["original_filename"] == filename
    assert document["processing_status"] == "completed"
    assert document["metadata"]["document_type"] == document_type
    assert document["metadata"]["character_count"] > 0
    assert document["metadata"]["chunk_count"] >= 1

    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).all()
        assert len(chunks) == document["metadata"]["chunk_count"]
        assert all(chunk.embedding is not None for chunk in chunks)
        assert chunks[0].chunk_metadata["start_character"] == 0
        assert chunks[0].chunk_metadata["end_character"] > 0
    finally:
        db.close()


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
    assert results[0]["metadata"]["start_character"] == 0
    assert results[0]["metadata"]["end_character"] > 0
    assert results[0]["start_character"] == 0
    assert results[0]["end_character"] > 0
    assert results[0]["distance"] == 0.0


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
                start_character=5,
                end_character=31,
                distance=0.25,
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
    body = response.json()
    assert body["response"] == "Used document context."
    assert body["metadata"]["knowledge"] == {
        "enabled": True,
        "mode": "planner",
        "retrieval_count": 1,
        "sources": [
            {
                "document_id": 1,
                "document_name": "notes.txt",
                "chunk_id": 10,
                "chunk_index": 0,
                "start_character": 5,
                "end_character": 31,
                "distance": 0.25,
            }
        ],
        "warning": None,
    }
    assert any(
        "Relevant document context." in message["content"]
        for message in observed_document_chunks
    )


def test_chat_old_request_shape_remains_compatible(monkeypatch, client):
    token = register_and_login(client)
    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "old-shape",
            "message": "Hello there.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Fake model response."
    assert body["metadata"]["knowledge"]["enabled"] is False
    assert body["metadata"]["knowledge"]["mode"] == "planner"
    assert body["metadata"]["knowledge"]["sources"] == []
    assert body["metadata"]["memory"]["enabled"] is True
    assert body["metadata"]["memory"]["mode"] == "planner"
    assert body["metadata"]["memory"]["sources"] == []


def test_chat_uses_saved_memory_across_conversations(client):
    token = register_and_login(client)
    observed_messages = []

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.append(messages)
            return "Your favorite programming language is Python."

    override_model_provider(ObservingModelProvider())
    client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "favorite_programming_language",
            "value": "Python",
        },
    )
    first_response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "first-memory-conversation",
            "message": "Hello there.",
        },
    )
    second_response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "second-memory-conversation",
            "message": "What is my favorite programming language?",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert any(
        "favorite_programming_language: Python" in item["content"]
        for item in observed_messages[1]
    )
    assert second_response.json()["metadata"]["memory"] == {
        "enabled": True,
        "mode": "planner",
        "retrieval_count": 1,
        "sources": [
            {
                "category": "preference",
                "key": "favorite_programming_language",
            }
        ],
    }


def test_chat_forced_memory_retrieval(client):
    token = register_and_login(client)
    observed_messages = []

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.extend(messages)
            return "forced memory response"

    override_model_provider(ObservingModelProvider())
    client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "favorite_language",
            "value": "Python",
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "forced-memory",
            "message": "favorite language",
            "memory_retrieval": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["memory"] == {
        "enabled": True,
        "mode": "explicit_enabled",
        "retrieval_count": 1,
        "sources": [
            {
                "category": "preference",
                "key": "favorite_language",
            }
        ],
    }
    assert any("favorite_language: Python" in item["content"] for item in observed_messages)


def test_chat_disabled_memory_retrieval_overrides_planner(client):
    token = register_and_login(client)
    observed_messages = []

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.extend(messages)
            return "disabled memory response"

    override_model_provider(ObservingModelProvider())
    client.post(
        "/memories",
        headers=auth_headers(token),
        json={
            "category": "preference",
            "key": "editor",
            "value": "VS Code",
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "disabled-memory",
            "message": "What do you remember about my editor?",
            "memory_retrieval": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["memory"] == {
        "enabled": False,
        "mode": "explicit_disabled",
        "retrieval_count": 0,
        "sources": [],
    }
    assert not any("editor: VS Code" in item["content"] for item in observed_messages)


def test_chat_forced_knowledge_retrieval(monkeypatch, client):
    token = register_and_login(client)
    observed_messages = []

    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.extend(messages)
            return "forced retrieval response"

    override_model_provider(ObservingModelProvider())
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "architecture.txt",
                b"Architecture notes for forced retrieval.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "forced",
            "message": "Tell me about architecture.",
            "knowledge_retrieval": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "forced retrieval response"
    assert body["metadata"]["knowledge"]["enabled"] is True
    assert body["metadata"]["knowledge"]["mode"] == "explicit_enabled"
    assert body["metadata"]["knowledge"]["retrieval_count"] == 1
    source = body["metadata"]["knowledge"]["sources"][0]
    assert source["document_name"] == "architecture.txt"
    assert source["start_character"] == 0
    assert source["end_character"] > 0
    assert source["distance"] == 0.0
    assert any(
        "Architecture notes for forced retrieval" in item["content"]
        for item in observed_messages
    )


def test_chat_disabled_knowledge_retrieval_overrides_planner(monkeypatch, client):
    token = register_and_login(client)
    observed_messages = []

    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    class ObservingModelProvider(FakeModelProvider):
        def generate(self, messages: list[dict]) -> str:
            observed_messages.extend(messages)
            return "disabled retrieval response"

    override_model_provider(ObservingModelProvider())
    client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "architecture.txt",
                b"Architecture notes that should not be injected.",
                "text/plain",
            )
        },
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "disabled",
            "message": "Search my documents for architecture.",
            "knowledge_retrieval": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "disabled retrieval response"
    assert body["metadata"]["knowledge"] == {
        "enabled": False,
        "mode": "explicit_disabled",
        "retrieval_count": 0,
        "sources": [],
        "warning": None,
    }
    assert not any(
        "Architecture notes that should not be injected" in item["content"]
        for item in observed_messages
    )


def test_chat_forced_knowledge_retrieval_no_results(monkeypatch, client):
    token = register_and_login(client)
    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "no-results",
            "message": "Hello there.",
            "knowledge_retrieval": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Fake model response."
    assert body["metadata"]["knowledge"] == {
        "enabled": True,
        "mode": "explicit_enabled",
        "retrieval_count": 0,
        "sources": [],
        "warning": None,
    }


def test_chat_vector_search_unavailable_returns_warning(monkeypatch, client):
    token = register_and_login(client)
    monkeypatch.setattr(
        "app.orchestrators.chat_orchestrator.extract_memory",
        lambda message: '{"remember": false}',
    )

    def unavailable(*args, **kwargs):
        raise VectorSearchUnavailableError("vector search unavailable")

    monkeypatch.setattr(
        "app.agents.knowledge_agent.retrieve_relevant_chunks",
        unavailable,
    )

    response = client.post(
        "/chat",
        headers=auth_headers(token),
        json={
            "conversation_id": "unavailable",
            "message": "Hello there.",
            "knowledge_retrieval": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Fake model response."
    assert body["metadata"]["knowledge"] == {
        "enabled": True,
        "mode": "explicit_enabled",
        "retrieval_count": 0,
        "sources": [],
        "warning": "vector search unavailable",
    }


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
    body = response.json()
    assert body["metadata"]["knowledge"]["retrieval_count"] == 1
    assert body["metadata"]["memory"]["retrieval_count"] == 1
    assert body["metadata"]["memory"]["sources"] == [
        {
            "category": "preference",
            "key": "editor",
        }
    ]
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
