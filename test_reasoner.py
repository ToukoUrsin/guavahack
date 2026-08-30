"""Planner boundary tests for provider-visible schema requirements."""

import json
import unittest
from unittest.mock import patch

# Ensure standalone test runs disable SDK telemetry before patching its helper.
import main  # noqa: F401
from adaptive_models import ActivityDefinition, Decision, Mode, Operation, SceneDefinition
from reasoner import Context, GuavaPlanner, Turn


class ReasonerTests(unittest.TestCase):
    def test_repair_schema_requires_the_payload_that_the_provider_omitted(self) -> None:
        request = "Let's rehearse asking for borrowed gear back"
        context = Context(
            trigger=request,
            origin_mode=Mode.COACH,
            user_requested=True,
            latest_caller=request,
            transcript=(Turn("caller", request, Mode.COACH),),
            scene=None,
            activity=None,
            moment=None,
            proposal=None,
        )
        valid = Decision(
            operation=Operation.CREATE,
            consent_quote=request,
            scene=SceneDefinition(
                title="Gear",
                situation="Borrowed gear is overdue",
                counterpart_description="Fictional friend",
                caller_role="The caller lent their gear",
                counterpart_role="The counterpart borrowed the gear",
                behavior="Deflects politely",
                caller_goal="Agree on a return day",
            ),
            activity=ActivityDefinition(objective="Practice asking for the gear back"),
        )

        def schema_following_provider(prompt: str, *, json_schema: dict) -> str:
            if {"scene", "activity"} <= set(json_schema.get("required", [])):
                return valid.model_dump_json()
            return json.dumps({"operation": "create", "scene": None, "activity": None})

        with patch("guava.helpers.llm.generate", side_effect=schema_following_provider) as generate:
            self.assertEqual(valid, GuavaPlanner().decide(context))
            self.assertEqual(2, generate.call_count)


if __name__ == "__main__":
    unittest.main()
