"""Offline tests for adaptive app wiring, channels, and safe logging."""

from __future__ import annotations

import logging
import os
import socket
import unittest
from unittest.mock import Mock, patch

# Import the app first: it disables SDK telemetry before loading Guava.
import main


class OfflineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """Fail loudly if any test attempts a network connection."""

        self.network_guard = patch.object(
            socket.socket, "connect", side_effect=AssertionError("Offline test attempted network")
        )
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)


class AgentWiringTests(OfflineTestCase):
    def test_create_agent_binds_supplied_controller_without_background_work(self) -> None:
        controller = Mock()
        with patch("guava.agent.Client") as client:
            agent = main.create_agent(controller)

        client.assert_called_once_with()
        controller.bind.assert_called_once_with(agent)
        self.assertEqual("Mira", agent._name)
        self.assertEqual("Second Draft", agent._organization)
        self.assertEqual("grace", agent._voice)


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
                    with patch("main.GUAVA_DEPLOY_TOKEN_PATH") as token_path:
                        token_path.exists.return_value = False
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

    def test_entrypoint_sanitizes_unexpected_errors(self) -> None:
        with patch.object(main, "run", side_effect=RuntimeError("private request body")):
            with self.assertLogs(main.logger, level="ERROR") as captured:
                result = main.entrypoint()

        self.assertEqual(1, result)
        output = "\n".join(captured.output)
        self.assertNotIn("private request body", output)
        self.assertIn("Runtime stopped (RuntimeError)", output)
