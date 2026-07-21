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
from app.tools import ToolContext


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

        action_result = self.action_agent.prepare_actions(plan, message)
        if knowledge_retrieval is False:
            action_result.actions = [
                action
                for action in action_result.actions
                if action.tool_name != "search_knowledge"
            ]
        agents_invoked.append(self.action_agent.name)
        tool_results, tool_executions = self._execute_actions(
            db=db,
            user_id=user_id,
            action_result=action_result,
            embedding_provider=embedding_provider,
        )

        if self._has_action(action_result, "list_documents"):
            knowledge_enabled = False
            plan.use_knowledge = False
        if self._has_action(action_result, "list_conversations"):
            memory_enabled = False
            knowledge_enabled = False
            plan.use_memory = False
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

        messages = build_chat_messages(
            message=message,
            history=history,
            memories=memory_context.memories,
            document_chunks=knowledge_context.chunks,
        )
        if tool_results:
            messages.append(
                {
                    "role": "system",
                    "content": self._format_tool_results_for_prompt(tool_results),
                }
            )

        deterministic_response = self._deterministic_tool_response(tool_results)
        if deterministic_response is not None:
            response = deterministic_response
            selected_provider = model_provider
        elif model_router:
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
                "actions": [
                    {
                        "tool_name": execution.name,
                        "status": execution.status,
                        "summary": execution.summary,
                    }
                    for execution in tool_executions
                ],
            },
        )

    def _execute_actions(
        self,
        db: Session,
        user_id: int,
        action_result,
        embedding_provider: EmbeddingProvider,
    ) -> tuple[list, list]:
        tool_results = []
        tool_executions = []
        context = ToolContext(
            db=db,
            user_id=user_id,
            embedding_provider=embedding_provider,
        )

        for action in action_result.actions[: self.action_agent.tool_registry.max_executions]:
            tool = self.action_agent.tool_registry.get(action.tool_name)
            if tool is not None and tool.destructive and not action.explicit_intent:
                result, execution = self.action_agent.tool_registry.execute(
                    context=context,
                    name="__blocked_destructive_action__",
                    arguments={},
                )
                execution.name = action.tool_name
                execution.summary = "Explicit user intent is required."
                result.summary = execution.summary
            else:
                result, execution = self.action_agent.tool_registry.execute(
                    context=context,
                    name=action.tool_name,
                    arguments=action.arguments,
                )
            tool_results.append(
                {
                    "name": execution.name,
                    "status": result.status,
                    "summary": result.summary,
                    "data": result.data,
                    "error": result.error,
                }
            )
            tool_executions.append(execution)

        if len(action_result.actions) > self.action_agent.tool_registry.max_executions:
            tool_executions.append(
                type(tool_executions[0])(
                    name="execution_limit",
                    status="error",
                    summary="Tool execution limit reached.",
                    error={
                        "code": "execution_limit_reached",
                        "message": "Tool execution limit reached.",
                    },
                )
            )

        return tool_results, tool_executions

    def _format_tool_results_for_prompt(self, tool_results: list[dict]) -> str:
        safe_results = [
            {
                "tool": result["name"],
                "status": result["status"],
                "summary": result["summary"],
                "data": result["data"],
                "error": result["error"],
            }
            for result in tool_results
        ]
        return (
            "Approved internal tool results for this user request:\n"
            f"{json.dumps(safe_results, default=str)}"
        )

    def _deterministic_tool_response(self, tool_results: list[dict]) -> str | None:
        if len(tool_results) != 1:
            return None

        result = tool_results[0]
        if result["status"] != "success":
            return result["summary"]

        name = result["name"]
        data = result["data"]
        if name == "save_memory":
            memory = data["memory"]
            return f"Saved to memory: {memory['key']} is {memory['value']}."
        if name == "delete_memory":
            return "Deleted that memory."
        if name == "list_memories":
            memories = data["memories"]
            if not memories:
                return "You do not have any saved memories yet."
            lines = [f"- {memory['key']}: {memory['value']}" for memory in memories]
            return "Your saved memories:\n" + "\n".join(lines)
        if name == "list_documents":
            documents = data["documents"]
            if not documents:
                return "You do not have any documents yet."
            lines = [
                f"- {document['original_filename']} ({document['processing_status']})"
                for document in documents
            ]
            return "Your documents:\n" + "\n".join(lines)
        if name == "list_conversations":
            conversations = data["conversations"]
            if not conversations:
                return "You do not have any conversations yet."
            lines = [
                f"- {conversation['title']} ({conversation['message_count']} messages)"
                for conversation in conversations
            ]
            return "Your conversations:\n" + "\n".join(lines)

        return None

    def _has_action(self, action_result, tool_name: str) -> bool:
        return any(action.tool_name == tool_name for action in action_result.actions)

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
