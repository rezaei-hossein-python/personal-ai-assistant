from app.agents.types import EvaluationResult, KnowledgeContext, MemoryContext, Plan


class EvaluatorAgent:
    name = "EvaluatorAgent"

    def evaluate_context(
        self,
        plan: Plan,
        memory_context: MemoryContext,
        knowledge_context: KnowledgeContext,
        response: str,
    ) -> EvaluationResult:
        warnings = []

        if plan.use_knowledge and not knowledge_context.chunks:
            warnings.append("knowledge_context_requested_but_empty")

        if plan.use_memory and not memory_context.memories:
            warnings.append("memory_context_requested_but_empty")

        if not response.strip():
            warnings.append("empty_model_response")

        return EvaluationResult(
            warnings=warnings,
            metadata={
                "warning_count": len(warnings),
            },
        )
