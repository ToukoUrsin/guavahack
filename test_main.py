"""Offline tests using the installed Guava command models and event dispatcher."""

import os
import logging
import socket
import unittest
from collections.abc import Callable
from typing import TypeVar
from unittest.mock import patch

# Import the app first: it disables SDK telemetry before loading Guava.
import main
from guava.commands import RetryTaskCommand, SendInstructionCommand, SetPersona, SetTaskCommand
from guava.events import (
    ActionItemCompletedEvent,
    CallerSpeechEvent,
    DTMFPressedEvent,
    EscalateEvent,
    TaskCompletedEvent,
)
from guava.testing import MockCall
from pydantic import BaseModel

CommandT = TypeVar("CommandT", bound=BaseModel)


def latest_command(call: MockCall, command_type: type[CommandT]) -> CommandT:
    return next(
        command for command in reversed(call._command_queue) if isinstance(command, command_type)
    )


def prepared_call(stage: main.Stage = main.Stage.INTAKE) -> MockCall:
    call = MockCall()
    call.set_variable(main.STAGE_KEY, stage.value)
    for key, value in {
        "relationship": "partner",
        "scenario": "We keep missing plans we made together",
        "desired_outcome": "Agree on a reliable plan",
        "difficulty": "realistic",
        "roleplay_consent": "yes",
    }.items():
        call.set_field(key, value)
    call._command_queue.clear()
    return call


class OfflineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # Any accidental network use fails rather than silently contacting Guava.
        self.network_guard = patch.object(
            socket.socket, "connect", side_effect=AssertionError("Offline test attempted network")
        )
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)


class ConversationFlowTests(OfflineTestCase):
    def test_call_starts_with_ai_disclosure_and_sensitive_intake(self) -> None:
        call = MockCall()
        main.on_call_start(call)

        persona = latest_command(call, SetPersona)
        task = latest_command(call, SetTaskCommand)
        self.assertEqual(main.Stage.INTAKE, call.get_variable(main.STAGE_KEY))
        self.assertEqual(main.COACH_NAME, persona.agent_name)
        self.assertEqual("intake", task.task_id)
        fields = {item.key: item for item in task.action_items if item.item_type == "field"}
        self.assertTrue(fields["scenario"].sensitive)
        self.assertTrue(fields["desired_outcome"].sensitive)
        self.assertEqual(["yes", "no"], fields["roleplay_consent"].choices)
        greeting = task.action_items[0]
        self.assertEqual("say", greeting.item_type)
        if greeting.item_type == "say":
            self.assertIn("AI", greeting.statement)

    def test_intake_switches_to_fictional_roleplay(self) -> None:
        call = prepared_call()
        main.on_intake_complete(call)

        persona = latest_command(call, SetPersona)
        task = latest_command(call, SetTaskCommand)
        self.assertEqual("Alex", persona.agent_name)
        self.assertIn("fictional", persona.agent_purpose or "")
        self.assertIn("We keep missing plans", persona.agent_purpose or "")
        self.assertEqual("rehearsal", task.task_id)
        self.assertIn("three", task.completion_criteria or "")

    def test_missing_consent_never_starts_roleplay(self) -> None:
        for consent in ("no", "", None, True):
            with self.subTest(consent=consent):
                call = prepared_call()
                call.set_field("roleplay_consent", consent)
                main.on_intake_complete(call)
                self.assertEqual(main.Stage.ENDED, call.get_variable(main.STAGE_KEY))
                self.assertFalse(any(isinstance(c, SetTaskCommand) for c in call._command_queue))

    def test_missing_scenario_retries_intake(self) -> None:
        call = prepared_call()
        call.set_field("scenario", "  ")
        main.on_intake_complete(call)
        self.assertEqual(main.Stage.INTAKE, call.get_variable(main.STAGE_KEY))
        self.assertIn("scenario", latest_command(call, RetryTaskCommand).reason)

    def test_rehearsal_returns_to_coach_for_debrief(self) -> None:
        call = prepared_call(main.Stage.REHEARSAL)
        main.on_rehearsal_complete(call)

        persona = latest_command(call, SetPersona)
        task = latest_command(call, SetTaskCommand)
        self.assertEqual(main.COACH_NAME, persona.agent_name)
        self.assertEqual("debrief", task.task_id)
        fields = {item.key: item for item in task.action_items if item.item_type == "field"}
        self.assertEqual(["try again", "finish"], fields["next_step"].choices)

    def test_try_again_creates_one_exchange_do_over(self) -> None:
        call = prepared_call(main.Stage.DEBRIEF)
        call.set_field("next_step", "try again")
        main.on_debrief_complete(call)
        task = latest_command(call, SetTaskCommand)
        self.assertEqual("do_over", task.task_id)
        self.assertIn("one caller line", task.completion_criteria or "")

    def test_finish_and_do_over_both_collect_takeaway(self) -> None:
        call = prepared_call(main.Stage.DEBRIEF)
        call.set_field("next_step", "finish")
        main.on_debrief_complete(call)
        self.assertEqual("takeaway", latest_command(call, SetTaskCommand).task_id)

        call = prepared_call(main.Stage.DO_OVER)
        main.on_do_over_complete(call)
        self.assertEqual("takeaway", latest_command(call, SetTaskCommand).task_id)

    def test_takeaway_closes_once_with_rehearsal_boundary(self) -> None:
        call = prepared_call(main.Stage.TAKEAWAY)
        main.on_takeaway_complete(call)
        instruction = latest_command(call, SendInstructionCommand)
        self.assertIn("not a prediction", instruction.instruction)
        command_count = len(call._command_queue)
        main.on_takeaway_complete(call)
        self.assertEqual(command_count, len(call._command_queue))

    def test_complete_flow_through_real_sdk_dispatcher(self) -> None:
        # Only authentication/client creation is mocked, not callbacks or models.
        with patch("guava.agent.Client"):
            agent = main.create_agent()
        call = prepared_call()
        agent._dispatch_event(call, TaskCompletedEvent(task_id="intake"))
        agent._dispatch_event(call, TaskCompletedEvent(task_id="rehearsal"))
        agent._dispatch_event(call, ActionItemCompletedEvent(key="next_step", payload="try again"))
        agent._dispatch_event(call, TaskCompletedEvent(task_id="debrief"))
        agent._dispatch_event(call, TaskCompletedEvent(task_id="do_over"))
        agent._dispatch_event(call, TaskCompletedEvent(task_id="takeaway"))
        self.assertEqual(
            ["rehearsal", "debrief", "do_over", "takeaway"],
            [c.task_id for c in call._command_queue if isinstance(c, SetTaskCommand)],
        )
        self.assertEqual(main.Stage.ENDED, call.get_variable(main.STAGE_KEY))


class ControlsAndSafetyTests(OfflineTestCase):
    def test_crisis_exit_is_sticky_and_duplicate_updates_do_nothing(self) -> None:
        call = prepared_call(main.Stage.REHEARSAL)
        event = CallerSpeechEvent(utterance="I think I want to hurt myself", utterance_id="a")
        main.on_caller_speech(call, event)
        task = latest_command(call, SetTaskCommand)
        self.assertEqual("safety_exit", task.task_id)
        greeting = task.action_items[0]
        if greeting.item_type == "say":
            self.assertIn("988", greeting.statement)
            self.assertIn("Elsewhere", greeting.statement)
        command_count = len(call._command_queue)
        main.on_caller_speech(call, event)

        callbacks: tuple[Callable[[MockCall], None], ...] = (
            main.on_intake_complete,
            main.on_rehearsal_complete,
            main.on_debrief_complete,
            main.on_do_over_complete,
            main.on_takeaway_complete,
        )
        for callback in callbacks:
            callback(call)
        main.on_caller_speech(call, CallerSpeechEvent(utterance="coach"))
        self.assertEqual(command_count, len(call._command_queue))
        self.assertEqual(main.Stage.SAFETY_EXIT, call.get_variable(main.STAGE_KEY))

    def test_safety_resources_do_not_automatically_hang_up(self) -> None:
        call = prepared_call(main.Stage.SAFETY_EXIT)
        main.on_safety_exit_complete(call)
        self.assertEqual(main.Stage.SAFETY_EXIT, call.get_variable(main.STAGE_KEY))
        self.assertIn("Do not resume", latest_command(call, SendInstructionCommand).instruction)

    def test_ordinary_conversation_does_not_trigger_exit(self) -> None:
        call = prepared_call(main.Stage.REHEARSAL)
        main.on_caller_speech(call, CallerSpeechEvent(utterance="I need to say I felt ignored"))
        self.assertEqual([], call._command_queue)

    def test_pause_during_rehearsal_or_do_over_returns_to_coach(self) -> None:
        stages = {
            main.Stage.REHEARSAL: main.Stage.DEBRIEF,
            main.Stage.DO_OVER: main.Stage.TAKEAWAY,
        }
        for stage, destination in stages.items():
            with self.subTest(stage=stage):
                call = prepared_call(stage)
                main.on_caller_speech(call, CallerSpeechEvent(utterance="Coach!", utterance_id="p"))
                main.on_caller_speech(call, CallerSpeechEvent(utterance="Coach!", utterance_id="p"))
                self.assertEqual(destination, call.get_variable(main.STAGE_KEY))
                self.assertEqual(1, sum(isinstance(c, SetTaskCommand) for c in call._command_queue))

    def test_goodbye_inside_a_scene_is_not_a_hangup_command(self) -> None:
        call = prepared_call(main.Stage.REHEARSAL)
        main.on_caller_speech(call, CallerSpeechEvent(utterance="Goodbye."))
        main.on_caller_speech(call, CallerSpeechEvent(utterance="No thanks."))
        self.assertEqual([], call._command_queue)

    def test_ordinary_concern_about_feelings_is_not_a_crisis_match(self) -> None:
        self.assertFalse(main._contains_crisis_language("I don't want to hurt someone emotionally"))

    def test_end_call_works_from_every_active_stage(self) -> None:
        for stage in main.Stage:
            with self.subTest(stage=stage):
                call = prepared_call(stage)
                main.on_caller_speech(call, CallerSpeechEvent(utterance="End call."))
                self.assertEqual(main.Stage.ENDED, call.get_variable(main.STAGE_KEY))

    def test_dtmf_pause_and_end_controls(self) -> None:
        call = prepared_call(main.Stage.REHEARSAL)
        main.on_dtmf(call, DTMFPressedEvent(digit="0"))
        self.assertEqual(main.Stage.DEBRIEF, call.get_variable(main.STAGE_KEY))
        main.on_dtmf(call, DTMFPressedEvent(digit="9"))
        self.assertEqual(main.Stage.ENDED, call.get_variable(main.STAGE_KEY))

    def test_human_handoff_request_leaves_roleplay_without_pretend_transfer(self) -> None:
        call = prepared_call(main.Stage.REHEARSAL)
        main.on_escalate(call, EscalateEvent(requested_by="human"))
        self.assertEqual(main.Stage.SAFETY_EXIT, call.get_variable(main.STAGE_KEY))


class ChannelTests(OfflineTestCase):
    def test_hosted_default_uses_phone_without_reading_the_credential(self) -> None:
        with patch("main.GUAVA_DEPLOY_TOKEN_PATH") as token_path:
            token_path.exists.return_value = True
            with patch.dict(os.environ, {"GUAVA_AGENT_NUMBER": "+15555555555"}, clear=True):
                with patch("main.create_agent") as create_agent:
                    main.run()
                    create_agent.return_value.listen_phone.assert_called_once_with("+15555555555")
            token_path.read_text.assert_not_called()

    def test_hosted_runtime_rejects_local_audio_or_terminal_chat(self) -> None:
        with patch("main.GUAVA_DEPLOY_TOKEN_PATH") as token_path:
            token_path.exists.return_value = True
            for channel in ("local", "chat"):
                with self.subTest(channel=channel):
                    with patch.dict(os.environ, {"GUAVA_CHANNEL": channel}, clear=True):
                        with patch("main.create_agent") as create_agent:
                            with self.assertRaisesRegex(main.ConfigurationError, "Hosted"):
                                main.run()
                            create_agent.assert_not_called()

    def test_local_default_remains_local_audio(self) -> None:
        with patch("main.GUAVA_DEPLOY_TOKEN_PATH") as token_path:
            token_path.exists.return_value = False
            with patch.dict(os.environ, {}, clear=True):
                with patch("main.create_agent") as create_agent:
                    main.run()
                    create_agent.return_value.call_local.assert_called_once_with()

    def test_phone_mode_requires_valid_number_before_authentication(self) -> None:
        for number in ("", "4155551212", "+1abc", "+01234567"):
            with self.subTest(number=number):
                with patch.dict(
                    os.environ, {"GUAVA_CHANNEL": "phone", "GUAVA_AGENT_NUMBER": number}, clear=True
                ):
                    with patch("main.create_agent") as create_agent:
                        with self.assertRaisesRegex(ValueError, "E.164"):
                            main.run()
                        create_agent.assert_not_called()

    def test_unknown_channel_is_rejected_before_authentication(self) -> None:
        with patch.dict(os.environ, {"GUAVA_CHANNEL": "carrier-pigeon"}, clear=True):
            with patch("main.create_agent") as create_agent:
                with self.assertRaisesRegex(ValueError, "local, chat, webrtc, phone"):
                    main.run()
                create_agent.assert_not_called()

    def test_channels_only_invoke_selected_entrypoint(self) -> None:
        methods = {
            "local": "call_local",
            "chat": "chat",
            "webrtc": "listen_webrtc",
            "phone": "listen_phone",
        }
        for channel, method in methods.items():
            with self.subTest(channel=channel):
                with patch.dict(
                    os.environ,
                    {"GUAVA_CHANNEL": channel, "GUAVA_AGENT_NUMBER": "+15555555555"},
                    clear=True,
                ):
                    with patch("main.create_agent") as create_agent:
                        main.run()
                        self.assertEqual(1, len(create_agent.return_value.method_calls))
                        self.assertEqual(method, create_agent.return_value.method_calls[0][0])


class PrivateLoggingTests(OfflineTestCase):
    def test_sdk_info_does_not_expose_scenario_text(self) -> None:
        record = logging.LogRecord(
            "guava.agent",
            logging.INFO,
            "sdk.py",
            1,
            "Received question: %s",
            ("synthetic-private-text",),
            None,
        )
        self.assertFalse(main.PrivateConsoleFilter().filter(record))

    def test_sdk_errors_remove_arguments_and_tracebacks(self) -> None:
        exception = ValueError("synthetic-private-text")
        record = logging.LogRecord(
            "guava.auth",
            logging.ERROR,
            "sdk.py",
            1,
            "Request failed: %s",
            ("synthetic-private-text",),
            (ValueError, exception, None),
        )
        record.exc_text = "synthetic-private-text"
        record.stack_info = "synthetic-private-text"
        self.assertTrue(main.PrivateConsoleFilter().filter(record))
        self.assertNotIn("synthetic-private-text", logging.Formatter().format(record))

    def test_runtime_does_not_print_raw_exception_details(self) -> None:
        with patch("main.configure_logging"):
            with patch("main.run", side_effect=RuntimeError("synthetic-private-text")):
                with self.assertLogs(main.logger, level="ERROR") as captured:
                    self.assertEqual(1, main.entrypoint())
        self.assertNotIn("synthetic-private-text", " ".join(captured.output))
        self.assertIn("RuntimeError", " ".join(captured.output))


if __name__ == "__main__":
    unittest.main()
