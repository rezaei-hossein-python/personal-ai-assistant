import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agents.action_agent import ActionAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.types import AgentExecutionMetadata
from app.core.logging import logger
from app.providers.model_provider import ModelProvider
from app.providers.model_router import ModelRouter
from app.services.conversation_service import get_or_create_conversation
from app.services.embedding_service import EmbeddingProvider
from app.services.memory_extractor import extract_memory
from app.services.memory_service import save_memory
from app.services.message_service import get_messages, save_message
from app.services.prompt_service import build_chat_messages


@dataclass
class ChatResult:
    response: str
    metadata: dict


class ChatOrchestrator:
    def __init__(
        self,
        planner_agent: PlannerAgent | None = None,
        memory_agent: MemoryAgent | None = None,
        knowledge_agent: KnowledgeAgent | None = None,
        action_agent: ActionAgent | None = None,
        evaluator_agent: EvaluatorAgent | None = None,
    ):
        self.planner_agent = planner_agent or PlannerAgent()
        self.memory_agent = memory_agent or MemoryAgent()
        self.knowledge_agent = knowledge_agent or KnowledgeAgent()
        self.action_agent = action_agent or ActionAgent()
        self.evaluator_agent = evaluator_agent or EvaluatorAgent()
        self.last_execution_metadata: AgentExecutionMetadata | None = None

    def handle_chat(
        self,
        db: Session,
        user_id: int,
        conversation_id: str,
        message: str,
        model_provider: ModelProvider,
        embedding_provider: EmbeddingProvider,
        model_router: ModelRouter | None = None,
        knowledge_retrieval: bool | None = None,
        memory_retrieval: bool | None = None,
    ) -> ChatResult:
        plan = self.planner_agent.plan(message)
        agents_invoked = [self.planner_agent.name]
        route = None
        memory_mode = "planner"
        memory_enabled = plan.use_memory
        knowledge_mode = "planner"
        knowledge_enabled = plan.use_knowledge

        if memory_retrieval is True:
            memory_mode = "explicit_enabled"
            memory_enabled = True
            plan.use_memory = True
        elif memory_retrieval is False:
            memory_mode = "explicit_disabled"
            memory_enabled = False
            plan.use_memory = False

        if knowledge_retrieval is True:
            knowledge_mode = "explicit_enabled"
            knowledge_enabled = True
            plan.use_knowledge = True
        elif knowledge_retrieval is False:
            knowledge_mode = "explicit_disabled"
            knowledge_enabled = False
            plan.use_knowledge = False

        get_or_create_conversation(
            db,
            conversation_id,
            user_id,
        )

        save_message(
            db,
            conversation_id,
            "user",
            message,
            user_id,
        )

        history = get_messages(
            db,
            conversation_id,
            user_id,
        )

        memory_context = self.memory_agent.get_context(
            db=db,
            user_id=user_id,
            query=message,
            enabled=memory_enabled,
        )
        memory_context.metadata["mode"] = memory_mode
        agents_invoked.append(self.memory_agent.name)

        knowledge_context = self.knowledge_agent.get_context(
            db=db,
            user_id=user_id,
            query=message,
            enabled=knowledge_enabled,
            embedding_provider=embedding_provider,
        )
        knowledge_context.metadata["mode"] = knowledge_mode
        agents_invoked.append(self.knowledge_agent.name)

        self.action_agent.prepare_actions(plan)
        agents_invoked.append(self.action_agent.name)

        messages = build_chat_messages(
            message=message,
            history=history,
            memories=memory_context.memories,
            document_chunks=knowledge_context.chunks,
        )
        if model_router:
            route = model_router.route(plan, message)
            collaboration_analyses = model_router.collaborate(route, messages)
            if collaboration_analyses:
                messages = messages + [
                    {
                        "role": "system",
                        "content": (
                            "Additional model analyses for synthesis:\n"
                            + "\n\n".join(collaboration_analyses)
                        ),
                    }
                ]
            response = model_router.generate_with_fallback(route, messages)
            selected_provider = route.provider
        else:
            response = model_provider.generate(messages)
            selected_provider = model_provider

        evaluation = self.evaluator_agent.evaluate_context(
            plan=plan,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
            response=response,
        )
        agents_invoked.append(self.evaluator_agent.name)

        save_message(
            db,
            conversation_id,
            "assistant",
            response,
            user_id,
        )

        self.last_execution_metadata = AgentExecutionMetadata(
            selected_intent=plan.intent.value,
            agents_invoked=agents_invoked,
            retrieval_count=len(knowledge_context.chunks),
            provider=selected_provider.provider_name,
            model=selected_provider.generation_model,
            evaluation_warnings=evaluation.warnings,
            selected_provider=selected_provider.provider_name,
            selected_model=selected_provider.generation_model,
            preferred_provider=(
                route.preferred_provider if route else selected_provider.provider_name
            ),
            fallback_events=[
                fallback.__dict__ for fallback in route.fallback_events
            ] if route else [],
            providers_invoked=(
                route.providers_invoked if route else [selected_provider.provider_name]
            ),
            collaboration_mode_used=route.collaboration_mode if route else False,
        )
        logger.info(
            "Chat orchestration completed",
            extra={
                "execution_metadata": self.last_execution_metadata.__dict__,
            },
        )

        return ChatResult(
            response=response,
            metadata={
                "knowledge": {
                    "enabled": knowledge_context.metadata.get("enabled", False),
                    "mode": knowledge_mode,
                    "retrieval_count": len(knowledge_context.chunks),
                    "sources": [
                        {
                            "document_id": chunk.document_id,
                            "document_name": chunk.document_name,
                            "chunk_id": chunk.chunk_id,
                            "chunk_index": chunk.chunk_index,
                            "start_character": chunk.start_character,
                            "end_character": chunk.end_character,
                            "distance": chunk.distance,
                        }
                        for chunk in knowledge_context.chunks
                    ],
                    "warning": knowledge_context.metadata.get("warning"),
                },
                "memory": {
                    "enabled": memory_context.metadata.get("enabled", False),
                    "mode": memory_mode,
                    "retrieval_count": len(memory_context.memories),
                    "sources": [
                        {
                            "category": memory.category,
                            "key": memory.key,
                        }
                        for memory in memory_context.memories
                    ],
                },
            },
        )

    def _extract_and_store_memory(
        self,
        db: Session,
        user_id: int,
        message: str,
    ) -> None:
        try:
            memory_result = extract_memory(message)
            memory_data = json.loads(memory_result)

            if memory_data.get("remember"):
                save_memory(
                    db=db,
                    user_id=user_id,
                    category=memory_data["category"],
                    key=memory_data["key"],
                    value=memory_data["value"],
                )
        except Exception as exc:
            logger.error(f"Memory extraction failed: {exc}")
