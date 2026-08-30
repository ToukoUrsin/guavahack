"""Behavioral tests for dynamic activities, replay memory, and cancellation."""

from __future__ import annotations

import socket
import threading
import unittest
from collections import deque
from collections.abc import Callable
from unittest.mock import patch

from guava.commands import SendInstructionCommand, SetTaskCommand
from guava.events import (
    AgentSpeechEvent,
    BotSessionEnded,
    CallerSpeechEvent,
    DTMFPressedEvent,
    TaskCompletedEvent,
)
from guava.testing import MockCall

import main  # Sets telemetry policy before Guava loads.
from adaptive import WAITING_FOR_PLAN, Controller, ThreadScheduler, check_consent
from adaptive_models import (
    ActivityDefinition,
    ClarificationField,
    Decision,
    Mode,
    Operation,
    SceneDefinition,
)
from reasoner import Context, Turn


def scene(behavior: str = "Politely changes the subject") -> SceneDefinition:
    return SceneDefinition(
        title="Borrowed climbing gear",
        situation="A friend has not returned borrowed gear",
        counterpart_description="A fictional climbing friend",
        caller_role="The caller lent their climbing gear and wants it returned",
        counterpart_role="The counterpart borrowed the caller's climbing gear",
        behavior=behavior,
        caller_goal="Agree on a specific day to return the gear",
        known_facts=("I lent climbing gear last month",),
    )


ACTIVITY = ActivityDefinition(objective="Rehearse the gear-return conversation in character.")


class Jobs:
    def __init__(self) -> None:
        self.jobs: deque[Callable[[], None]] = deque()

    def submit(self, job: Callable[[], None]) -> None:
        self.jobs.append(job)

    def run(self) -> None:
        while self.jobs:
            self.jobs.popleft()()


class ScriptedPlanner:
    def __init__(self) -> None:
        self.decisions: deque[Decision] = deque()
        self.contexts: list[Context] = []
        self.hook: Callable[[], None] | None = None

    def decide(self, context: Context) -> Decision:
        self.contexts.append(context)
        if self.hook:
            hook, self.hook = self.hook, None
            hook()
        return self.decisions.popleft()


class AdaptiveTests(unittest.TestCase):
    def setUp(self) -> None:
        guard = patch.object(
            socket.socket, "connect", side_effect=AssertionError("Network forbidden")
        )
        guard.start()
        self.addCleanup(guard.stop)
        self.planner = ScriptedPlanner()
        self.jobs = Jobs()
        self.controller = Controller(self.planner, self.jobs)
        self.call = MockCall()
        self.controller.on_start(self.call)
        session = self.controller.session(self.call)
        assert session is not None
        self.session = session

    def say(self, text: str, utterance_id: str | None = None) -> None:
        self.controller.on_caller(
            self.call, CallerSpeechEvent(utterance=text, utterance_id=utterance_id)
        )

    def request(self, text: str, decision: Decision) -> None:
        self.say(text)
        self.planner.decisions.append(decision)
        suggestion = self.controller.on_action_request(self.call, text)
        assert suggestion is not None
        self.controller.on_action(self.call, suggestion.key)

    def start_scene(self) -> None:
        self.request(
            "I lent climbing gear last month. Let's rehearse this",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="rehearse this",
            ),
        )
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)

    def test_invented_details_do_not_become_known_caller_facts(self) -> None:
        proposed = scene().model_copy(
            update={
                "known_facts": (
                    "I lent climbing gear last month",
                    "The gear is for an upcoming trip",
                )
            }
        )
        self.request(
            "I lent climbing gear last month. Let's rehearse",
            Decision(
                operation=Operation.CREATE,
                scene=proposed,
                activity=ACTIVITY,
                consent_quote="Let's rehearse",
            ),
        )
        self.jobs.run()
        assert self.session.scene is not None
        self.assertEqual(("I lent climbing gear last month",), self.session.scene.known_facts)

    def exchange(self) -> None:
        self.say("Could I get my gear back on Friday?")
        self.controller.on_agent(
            self.call, AgentSpeechEvent(utterance="Friday? I might need another day.")
        )

    def test_ordinary_conversation_can_continue_without_planner_or_turn_limit(self) -> None:
        for index in range(40):
            self.say(f"Here is another detail, {index}", str(index))
            self.controller.on_agent(self.call, AgentSpeechEvent(utterance="Tell me more."))
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertEqual([], self.planner.contexts)
        self.assertEqual(1, sum(isinstance(c, SetTaskCommand) for c in self.call._command_queue))
        self.assertLessEqual(len(self.session.turns), 48)

    def test_generated_scene_and_activity_reach_real_guava_commands(self) -> None:
        self.start_scene()
        self.assertEqual(scene(), self.session.scene)
        tasks = [c for c in self.call._command_queue if isinstance(c, SetTaskCommand)]
        self.assertIn(ACTIVITY.objective, tasks[-1].objective)
        self.assertFalse(any(item.item_type == "field" for item in tasks[-1].action_items))

    def test_unrelated_or_old_quote_cannot_grant_consent(self) -> None:
        self.say("Yes, let's rehearse")
        self.request(
            "Not yet; I just want to discuss",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="let's rehearse",
            ),
        )
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertEqual(scene(), self.session.proposal)

    def test_retraction_cancels_queued_start(self) -> None:
        self.request(
            "Start the rehearsal",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="Start the rehearsal",
            ),
        )
        self.say("Actually, don't start yet")
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertIsNone(self.session.scene)

    def test_negative_practice_quote_is_not_consent(self) -> None:
        self.request(
            "I do not want to practice yet",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="practice yet",
            ),
        )
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)

    def test_casual_affirmation_from_phone_call_starts_the_scene(self) -> None:
        self.say("A fictional climbing friend has not returned my gear.")
        self.request(
            "Yeah, yeah, let's practice it.",
            Decision(
                operation=Operation.CREATE, scene=scene(), activity=ACTIVITY, consent_quote="Yeah"
            ),
        )
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)

    def test_spoken_agreement_triggers_switch_without_model_requesting_an_action(self) -> None:
        self.say("A friend has not returned my borrowed gear.")
        self.controller.on_agent(
            self.call, AgentSpeechEvent(utterance="Would you like to try a rehearsal now?")
        )
        self.planner.decisions.append(
            Decision(operation=Operation.CREATE, scene=scene(), activity=ACTIVITY)
        )
        self.say("Yeah.")
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)
        self.assertEqual(1, len(self.planner.contexts))
        suggestion = self.controller.on_action_request(self.call, "Start the agreed rehearsal")
        assert suggestion is not None
        self.controller.on_action(self.call, suggestion.key)
        self.jobs.run()
        self.assertEqual(1, len(self.planner.contexts), "Late action duplicated the speech request")

    def test_guava_can_reuse_an_offered_action_after_a_new_agreement(self) -> None:
        self.say("Offer me a rehearsal about the borrowed gear, but don't start yet.")
        suggestion = self.controller.on_action_request(self.call, "Offer a gear rehearsal")
        assert suggestion is not None
        self.planner.decisions.append(Decision(operation=Operation.STAY))
        self.controller.on_action(self.call, suggestion.key)
        self.jobs.run()
        self.controller.on_agent(
            self.call, AgentSpeechEvent(utterance="Would you like to try the rehearsal now?")
        )
        self.say("Yeah.")
        self.planner.decisions.append(
            Decision(operation=Operation.CREATE, scene=scene(), activity=ACTIVITY)
        )
        # Guava executes the SAME suggested key, without another action-request.
        self.controller.on_action(self.call, suggestion.key)
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)
        self.assertEqual("Yeah.", self.planner.contexts[-1].latest_caller)
        self.controller.on_action(self.call, suggestion.key)
        self.jobs.run()
        self.assertEqual(2, len(self.planner.contexts), "Duplicate delivery planned twice")
        self.say("Pause")
        self.say("Yeah.")
        self.controller.on_action(self.call, suggestion.key)
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode, "A stale action resumed after pause")

    def test_delayed_duplicate_after_ordinary_speech_does_not_plan_again(self) -> None:
        self.say("Let's rehearse returning borrowed gear")
        suggestion = self.controller.on_action_request(self.call, "Start rehearsal")
        assert suggestion is not None
        self.planner.decisions.append(
            Decision(operation=Operation.CREATE, scene=scene(), activity=ACTIVITY)
        )
        self.controller.on_action(self.call, suggestion.key)
        self.jobs.run()
        self.say("Could I get my gear back on Friday?")
        self.controller.on_action(self.call, suggestion.key)
        self.assertFalse(self.jobs.jobs)
        self.assertEqual(Mode.REHEARSAL, self.session.mode)

    def test_switch_diagnostics_do_not_log_dialogue(self) -> None:
        self.controller.on_agent(
            self.call, AgentSpeechEvent(utterance="Would you like to practice now?")
        )
        self.request(
            "Yeah, this is synthetic-private-dialogue",
            Decision(
                operation=Operation.CREATE, scene=scene(), activity=ACTIVITY, consent_quote="Yeah"
            ),
        )
        with self.assertLogs("second_draft", level="INFO") as logs:
            self.jobs.run()
        output = " ".join(logs.output)
        self.assertIn("current_agreement", output)
        self.assertNotIn("synthetic-private-dialogue", output)

    def test_spoken_agreement_variants_and_retractions(self) -> None:
        cases = (
            ("Yeah.", "yeah", True),
            ("Yep, let's do it.", "Yep", True),
            ("Yup", "yup", True),
            ("Let’s do it!", "let's do it", True),
            ("Yeah, that's fine.", "yeah thats fine", True),
            ("Yeah, not yet.", "yeah", False),
            ("Yeah, that's not what I want.", "yeah", False),
            ("I don't want to practice", "practice", False),
            ("Maybe later", "maybe later", False),
        )
        for utterance, quote, expected in cases:
            with self.subTest(utterance=utterance):
                context = Context(
                    trigger="Practice request",
                    origin_mode=Mode.COACH,
                    user_requested=True,
                    latest_caller=utterance,
                    transcript=(
                        Turn("agent", "Would you like to rehearse now?", Mode.COACH),
                        Turn("caller", utterance, Mode.COACH),
                    ),
                    scene=None,
                    activity=None,
                    moment=None,
                    proposal=None,
                )
                decision = Decision(
                    operation=Operation.CREATE,
                    scene=scene(),
                    activity=ACTIVITY,
                    consent_quote=quote,
                )
                self.assertEqual(expected, check_consent(context, decision.operation)[0])

    def test_unrelated_backchannel_does_not_start_a_scene(self) -> None:
        context = Context(
            trigger="Possible practice",
            origin_mode=Mode.COACH,
            user_requested=True,
            latest_caller="Yeah",
            transcript=(
                Turn("agent", "Is that how it felt?", Mode.COACH),
                Turn("caller", "Yeah", Mode.COACH),
            ),
            scene=None,
            activity=None,
            moment=None,
            proposal=None,
        )
        decision = Decision(
            operation=Operation.CREATE, scene=scene(), activity=ACTIVITY, consent_quote="Yeah"
        )
        self.assertFalse(check_consent(context, decision.operation)[0])

    def test_replay_button_cannot_authorize_an_unrelated_new_scene(self) -> None:
        self.start_scene()
        self.exchange()
        self.say("Pause")
        original = self.session.scene
        self.planner.decisions.append(
            Decision(operation=Operation.CREATE, scene=scene("Unrelated"), activity=ACTIVITY)
        )
        self.controller.replay(self.call)
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertEqual(original, self.session.scene)

    def test_replay_without_a_saved_moment_does_not_call_the_planner(self) -> None:
        self.controller.replay(self.call)
        self.assertFalse(self.jobs.jobs)
        self.assertEqual(Mode.COACH, self.session.mode)

    def test_keypad_pause_replay_and_repeated_keypresses_share_the_state_guards(self) -> None:
        self.start_scene()
        self.exchange()
        self.controller.on_dtmf(self.call, DTMFPressedEvent(digit="0"))
        self.assertEqual(Mode.COACH, self.session.mode)
        self.planner.decisions.append(Decision(operation=Operation.REPLAY))
        self.controller.on_dtmf(self.call, DTMFPressedEvent(digit="1"))
        work = self.session.queued
        self.controller.on_dtmf(self.call, DTMFPressedEvent(digit="1"))
        self.assertIs(work, self.session.queued)
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)
        self.controller.on_dtmf(self.call, DTMFPressedEvent(digit="9"))
        self.assertEqual(Mode.ENDED, self.session.mode)

    def test_keypad_help_does_not_change_the_activity(self) -> None:
        task = self.session.active_task
        self.controller.on_dtmf(self.call, DTMFPressedEvent(digit="*"))
        self.assertEqual(task, self.session.active_task)
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertFalse(self.jobs.jobs)

    def test_keypad_zero_cancels_an_inflight_scene_start(self) -> None:
        self.request(
            "Let's rehearse",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="Let's rehearse",
            ),
        )
        self.controller.on_dtmf(self.call, DTMFPressedEvent(digit="0"))
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertIsNone(self.session.scene)
        self.assertIsNot(self.session.activity, WAITING_FOR_PLAN)

    def test_stay_restores_the_activity_after_preparation(self) -> None:
        original = self.session.activity
        self.request("Keep helping me think this through", Decision(operation=Operation.STAY))
        self.assertIs(self.session.activity, WAITING_FOR_PLAN)
        self.jobs.run()
        self.assertEqual(original, self.session.activity)

    def test_correction_keeps_scene_facts_and_the_relevant_exchange(self) -> None:
        self.start_scene()
        self.exchange()
        corrected = scene("Makes a gentle joke to deflect the request")
        self.request(
            "No, he would joke about it instead. Change that.",
            Decision(operation=Operation.REVISE, scene=corrected),
        )
        self.jobs.run()
        self.assertEqual(corrected, self.session.scene)
        self.assertEqual(Mode.REHEARSAL, self.session.mode)
        self.assertEqual(ACTIVITY, self.session.activity)
        assert self.session.moment is not None
        self.assertIn("Friday", self.session.moment.exchange[-1].text)
        self.assertFalse(any("Change that" in turn.text for turn in self.session.moment.exchange))

    def test_pause_and_replay_reconstruct_saved_moment_without_new_intake(self) -> None:
        self.start_scene()
        self.exchange()
        self.say("Pause. What could I say here?")
        self.assertEqual(Mode.COACH, self.session.mode)
        moment = self.session.moment
        self.request(
            "Try that moment again",
            Decision(operation=Operation.REPLAY, consent_quote="Try that moment again"),
        )
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)
        self.assertEqual(moment, self.session.moment)
        self.assertEqual(ACTIVITY, self.session.activity)

    def test_explicit_replay_does_not_depend_on_model_repeating_consent_words(self) -> None:
        self.start_scene()
        self.exchange()
        self.say("Pause")
        self.request("Try that exact moment again", Decision(operation=Operation.REPLAY))
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)

    def test_no_fixed_retry_limit(self) -> None:
        self.start_scene()
        self.exchange()
        for _ in range(5):
            self.say("Pause")
            self.request(
                "Try that moment again",
                Decision(operation=Operation.REPLAY, consent_quote="Try that moment again"),
            )
            self.jobs.run()
            self.assertEqual(Mode.REHEARSAL, self.session.mode)

    def test_old_background_decision_cannot_resume_after_pause(self) -> None:
        self.start_scene()
        self.exchange()
        self.request("Change the scene", Decision(operation=Operation.REVISE, scene=scene("Jokes")))
        self.planner.hook = lambda: self.say("Pause")
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertNotEqual("Jokes", self.session.scene.behavior if self.session.scene else None)

    def test_pause_invalidates_completion_of_the_previous_coach_activity(self) -> None:
        old_task = self.session.active_task
        self.request("Help me prepare", Decision(operation=Operation.STAY))
        self.say("Pause")
        self.controller.on_task_complete(self.call, old_task)
        self.assertIsNone(self.session.queued)
        self.jobs.run()
        self.assertEqual([], self.planner.contexts)

    def test_new_checkpoint_after_revision_excludes_the_previous_version(self) -> None:
        self.start_scene()
        self.exchange()
        old_generation = self.session.scene_generation
        self.request("He jokes instead", Decision(operation=Operation.REVISE, scene=scene("Jokes")))
        self.jobs.run()
        self.say("Could you put the gear in my locker tomorrow?")
        self.controller.on_agent(
            self.call, AgentSpeechEvent(utterance="My locker is a gear hotel!")
        )
        self.say("Pause")
        assert self.session.moment is not None
        self.assertTrue(
            all(turn.scene_generation != old_generation for turn in self.session.moment.exchange)
        )
        self.assertFalse(any("Friday" in turn.text for turn in self.session.moment.exchange))

    def test_pause_after_corrected_reply_keeps_the_original_caller_cue(self) -> None:
        self.start_scene()
        self.exchange()
        self.request("He jokes instead", Decision(operation=Operation.REVISE, scene=scene("Jokes")))
        self.jobs.run()
        self.controller.on_agent(
            self.call, AgentSpeechEvent(utterance="The gear enjoys living here! Friday works.")
        )
        self.say("Pause")
        assert self.session.moment is not None
        self.assertEqual(
            ["Could I get my gear back on Friday?"],
            [turn.text for turn in self.session.moment.exchange if turn.speaker == "caller"],
        )

    def test_immediate_pause_after_revision_replays_the_corrected_character(self) -> None:
        self.start_scene()
        self.exchange()
        corrected = scene("Uses humor")
        self.request("He jokes instead", Decision(operation=Operation.REVISE, scene=corrected))
        self.jobs.run()
        self.say("Pause")
        self.request("Replay that moment", Decision(operation=Operation.REPLAY))
        self.jobs.run()
        self.assertEqual(corrected, self.session.scene)

    def test_many_speech_chunks_cannot_drop_the_saved_caller_cue(self) -> None:
        self.start_scene()
        self.say("Could I get my gear back on Friday?")
        for index in range(8):
            self.controller.on_agent(self.call, AgentSpeechEvent(utterance=f"Reply part {index}"))
        self.say("Pause")
        assert self.session.moment is not None
        self.assertEqual("caller", self.session.moment.exchange[0].speaker)
        self.assertIn("Friday", self.session.moment.exchange[0].text)
        self.assertLessEqual(len(self.session.moment.exchange), 6)

    def test_new_request_replaces_inflight_decision_without_parallel_planning(self) -> None:
        self.start_scene()
        self.exchange()
        self.request("Change the scene", Decision(operation=Operation.REVISE, scene=scene("Old")))
        self.planner.hook = lambda: self.request(
            "Actually keep coaching",
            Decision(
                operation=Operation.COACH,
                activity=ActivityDefinition(objective="Explore a clear boundary"),
            ),
        )
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertEqual("Explore a clear boundary", self.session.activity.objective)
        self.assertNotEqual("Old", self.session.scene.behavior if self.session.scene else None)

    def test_invalid_planner_output_returns_to_coach_without_a_stuck_worker(self) -> None:
        self.request(
            "Let's rehearse",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="Let's rehearse",
            ),
        )

        def fail() -> None:
            raise ValueError("synthetic-private-response")

        self.planner.hook = fail
        with self.assertLogs("second_draft", level="WARNING") as logs:
            self.jobs.run()
        self.assertFalse(self.session.thinking)
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertNotIn("synthetic-private-response", " ".join(logs.output))

    def test_action_from_one_call_cannot_change_another_call(self) -> None:
        other = MockCall()
        self.controller.on_start(other)
        self.say("Let's rehearse")
        self.planner.decisions.append(
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="Let's rehearse",
            )
        )
        action = self.controller.on_action_request(self.call, "Start this scene")
        assert action is not None
        self.controller.on_action(other, action.key)
        self.assertFalse(self.jobs.jobs)
        self.controller.on_action(self.call, action.key)
        self.jobs.run()
        other_session = self.controller.session(other)
        assert other_session is not None
        self.assertEqual(Mode.REHEARSAL, self.session.mode)
        self.assertEqual(Mode.COACH, other_session.mode)
        self.assertIsNone(other_session.scene)

    def test_safety_and_end_cancel_plans_and_clear_session_memory(self) -> None:
        self.request(
            "Let's rehearse",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="Let's rehearse",
            ),
        )
        self.say("I want to hurt myself")
        self.jobs.run()
        self.assertEqual(Mode.SAFETY, self.session.mode)
        self.controller.replay(self.call)
        self.assertFalse(self.jobs.jobs)
        self.say("End call")
        self.assertEqual(Mode.ENDED, self.session.mode)
        self.controller.on_end(self.call, BotSessionEnded(termination_reason="bot-hangup"))
        self.assertIsNone(self.controller.session(self.call))
        self.assertEqual([], self.session.turns)

    def test_completed_activity_can_stay_open_but_cannot_invent_a_replay(self) -> None:
        self.planner.decisions.append(Decision(operation=Operation.STAY))
        previous = self.session.active_task
        self.controller.on_task_complete(self.call, previous)
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)
        self.assertNotEqual(previous, self.session.active_task)
        self.start_scene()
        self.exchange()
        self.planner.decisions.append(Decision(operation=Operation.REPLAY))
        self.controller.on_task_complete(self.call, self.session.active_task)
        self.jobs.run()
        self.assertEqual(Mode.COACH, self.session.mode)

    def test_task_completion_does_not_loop_planning_without_new_caller_input(self) -> None:
        self.planner.decisions.append(Decision(operation=Operation.STAY))
        self.controller.on_task_complete(self.call, self.session.active_task)
        self.jobs.run()
        self.controller.on_task_complete(self.call, self.session.active_task)
        self.assertFalse(self.jobs.jobs)
        self.assertEqual(1, len(self.planner.contexts))

    def test_task_completion_does_not_replace_an_explicit_request(self) -> None:
        self.request(
            "Let's rehearse",
            Decision(
                operation=Operation.CREATE,
                scene=scene(),
                activity=ACTIVITY,
                consent_quote="Let's rehearse",
            ),
        )
        work = self.session.queued
        self.controller.on_task_complete(self.call, self.session.active_task)
        self.assertIs(work, self.session.queued)
        self.jobs.run()
        self.assertEqual(Mode.REHEARSAL, self.session.mode)

    def test_generated_clarification_fields_are_retained_for_the_planner(self) -> None:
        activity = ActivityDefinition(
            objective="Clarify the boundary the caller wants",
            fields=(ClarificationField(key="boundary", question="What limit would feel fair?"),),
        )
        self.request(
            "Help me figure this out", Decision(operation=Operation.COACH, activity=activity)
        )
        self.jobs.run()
        self.call.set_field(f"{self.session.active_task}_boundary", "Return gear by Friday")
        self.planner.decisions.append(Decision(operation=Operation.STAY))
        self.controller.on_task_complete(self.call, self.session.active_task)
        self.jobs.run()
        self.assertEqual(
            "Return gear by Friday", dict(self.planner.contexts[-1].clarifications)["boundary"]
        )

    def test_asr_updates_replace_the_same_utterance(self) -> None:
        self.say("I want", "utterance-1")
        self.say("I want to discuss a problem", "utterance-1")
        self.assertEqual(1, len(self.session.turns))
        self.assertEqual("I want to discuss a problem", self.session.latest_caller)

    def test_real_sdk_dispatcher_uses_dynamic_task_and_action_callbacks(self) -> None:
        with patch("guava.agent.Client"):
            agent = main.create_agent(self.controller)
        self.planner.decisions.append(Decision(operation=Operation.STAY))
        agent._dispatch_event(self.call, TaskCompletedEvent(task_id=self.session.active_task))
        self.jobs.run()
        agent._dispatch_event(self.call, DTMFPressedEvent(digit="9"))
        self.assertEqual(Mode.ENDED, self.session.mode)
        self.assertTrue(
            any(
                isinstance(c, SendInstructionCommand) and "hang up" in c.instruction
                for c in self.call._command_queue
            )
        )

    def test_pause_is_not_blocked_by_a_slow_model_on_another_thread(self) -> None:
        started, release, paused = threading.Event(), threading.Event(), threading.Event()

        class SlowPlanner:
            def decide(self, context: Context) -> Decision:
                started.set()
                release.wait(3)
                return Decision(
                    operation=Operation.CREATE,
                    scene=scene(),
                    activity=ACTIVITY,
                    consent_quote="Let's rehearse",
                )

        scheduler = ThreadScheduler()
        controller = Controller(SlowPlanner(), scheduler)
        call = MockCall()
        controller.on_start(call)
        controller.on_caller(call, CallerSpeechEvent(utterance="Let's rehearse"))
        action = controller.on_action_request(call, "Let's rehearse")
        assert action is not None
        controller.on_action(call, action.key)

        def pause() -> None:
            controller.on_caller(call, CallerSpeechEvent(utterance="Pause"))
            paused.set()

        thread = threading.Thread(target=pause)
        try:
            self.assertTrue(started.wait(1))
            thread.start()
            self.assertTrue(paused.wait(0.5), "Pause waited for the model")
        finally:
            release.set()
            if thread.ident:
                thread.join(2)
            scheduler.pool.shutdown(wait=True)
        session = controller.session(call)
        assert session is not None
        self.assertEqual(Mode.COACH, session.mode)
        self.assertIsNone(session.scene)


if __name__ == "__main__":
    unittest.main()
