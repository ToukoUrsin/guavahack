"""Focused validation tests for adaptive decision models."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from adaptive_models import (
    ActivityDefinition,
    ClarificationField,
    Decision,
    Operation,
    SceneDefinition,
)


def valid_scene() -> SceneDefinition:
    return SceneDefinition(
        title="Discussing a changing project scope",
        situation="A colleague asks to expand the project after the agreed deadline.",
        counterpart_description="A capable colleague who is under deadline pressure.",
        caller_role="The caller owns the agreed project scope",
        counterpart_role="The counterpart is requesting extra work",
        behavior="They are direct and may push for an immediate commitment.",
        caller_goal="Set a clear boundary while preserving the working relationship.",
        known_facts=["The original scope was agreed last week."],
        boundaries=["Do not promise extra work during this conversation."],
    )


def valid_activity() -> ActivityDefinition:
    return ActivityDefinition(
        objective="Help the caller formulate and practice one clear boundary.",
        completion_criteria="Complete when the caller has a sentence they would use.",
        checklist=["Name the request.", "State the boundary.", "Offer one next step."],
        fields=[ClarificationField(key="desired_outcome", question="What outcome do you want?")],
    )


class AdaptiveModelsTests(unittest.TestCase):
    def test_valid_dynamic_scene_activity_and_create(self) -> None:
        scene = valid_scene()
        activity = valid_activity()
        decision = Decision(operation=Operation.CREATE, scene=scene, activity=activity)

        self.assertEqual(decision.scene, scene)
        self.assertEqual(decision.activity, activity)
        self.assertEqual(scene.counterpart_name, "Alex")

    def test_models_reject_extra_fields_and_are_frozen(self) -> None:
        with self.assertRaises(ValidationError):
            ClarificationField.model_validate(
                {"key": "goal", "question": "What matters?", "injected": "no"}
            )

        field = ClarificationField(key="goal", question="What matters?")
        with self.assertRaises(ValidationError):
            setattr(field, "required", True)

        activity = valid_activity()
        self.assertIsInstance(activity.checklist, tuple)
        self.assertIsInstance(activity.fields, tuple)

    def test_create_requires_scene_and_activity(self) -> None:
        with self.assertRaises(ValidationError):
            Decision(operation=Operation.CREATE, scene=valid_scene())
        with self.assertRaises(ValidationError):
            Decision(operation=Operation.CREATE, activity=valid_activity())

    def test_duplicate_field_keys_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ActivityDefinition(
                objective="Clarify the next step.",
                fields=[
                    ClarificationField(key="goal", question="What is your goal?"),
                    ClarificationField(key="goal", question="What would success look like?"),
                ],
            )

    def test_size_bounds_are_enforced(self) -> None:
        with self.assertRaises(ValidationError):
            ActivityDefinition(objective="")
        with self.assertRaises(ValidationError):
            ActivityDefinition(objective="x", checklist=["x"] * 7)
        with self.assertRaises(ValidationError):
            ClarificationField(key="bad-key", question="x")
        with self.assertRaises(ValidationError):
            SceneDefinition(
                title="x",
                situation="x",
                counterpart_description="x",
                caller_role="x",
                counterpart_role="x",
                behavior="x",
                caller_goal="x",
                known_facts=["x" * 501],
            )

    def test_enum_constraints_and_operation_payload_rules(self) -> None:
        with self.assertRaises(ValidationError):
            Decision(operation="unknown")
        with self.assertRaises(ValidationError):
            Decision(operation=Operation.STAY, scene=valid_scene())
        with self.assertRaises(ValidationError):
            Decision(operation=Operation.REVISE)
        with self.assertRaises(ValidationError):
            Decision(operation=Operation.COACH)

        replay = Decision(operation=Operation.REPLAY, scene=valid_scene())
        coach = Decision(operation=Operation.COACH, activity=valid_activity())
        end = Decision(operation=Operation.END, guidance="We can stop here.")
        safety = Decision(operation=Operation.SAFETY, consent_quote="Let's pause.")
        self.assertEqual(replay.operation, Operation.REPLAY)
        self.assertEqual(coach.operation, Operation.COACH)
        self.assertEqual(end.operation, Operation.END)
        self.assertEqual(safety.operation, Operation.SAFETY)


if __name__ == "__main__":
    unittest.main()
