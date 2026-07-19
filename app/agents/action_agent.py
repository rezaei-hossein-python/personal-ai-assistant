from app.agents.types import ActionResult, Plan


class ActionAgent:
    name = "ActionAgent"

    def prepare_actions(self, plan: Plan) -> ActionResult:
        return ActionResult(
            actions=[],
            metadata={
                "enabled": plan.allow_actions,
                "supported_actions": [],
            },
        )
