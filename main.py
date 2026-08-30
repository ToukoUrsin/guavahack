"""Second Draft: one continuous Guava call, guided by one planning agent."""

from __future__ import annotations

import logging
import os
import re

# Disable telemetry before loading Guava; raw exceptions can contain prompts.
os.environ["GUAVA_DISABLE_TELEMETRY"] = "true"

import guava
from guava import logging_utils
from guava.auth import GUAVA_DEPLOY_TOKEN_PATH

from adaptive import COACH_PURPOSE, Controller
from reasoner import GuavaPlanner

logger = logging.getLogger("second_draft")


class ConfigurationError(ValueError):
    """Safe-to-display errors containing known configuration keys, not values."""


class PrivateConsoleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == logger.name and not record.exc_info:
            return True
        if record.name == "guava.agent" and record.msg == "WebRTC URL: %s?webrtc_code=%s":
            return True
        if record.levelno < logging.WARNING:
            return False
        record.msg = "SDK reported a warning or error; raw diagnostic details withheld."
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def configure_logging() -> None:
    logging_utils.configure_logging()
    for handler in logging.getLogger().handlers:
        handler.addFilter(PrivateConsoleFilter())


def create_agent(controller: Controller | None = None) -> guava.Agent:
    agent = guava.Agent(
        name="Mira",
        organization="Second Draft",
        purpose=COACH_PURPOSE,
        voice="grace",
        accept_dtmf=False,
    )
    (controller or Controller(GuavaPlanner())).bind(agent)
    return agent


def run() -> None:
    hosted = GUAVA_DEPLOY_TOKEN_PATH.exists()
    channel = os.environ.get("GUAVA_CHANNEL", "phone" if hosted else "local").strip().casefold()
    if channel not in {"local", "chat", "webrtc", "phone"}:
        raise ConfigurationError("GUAVA_CHANNEL must be one of: local, chat, webrtc, phone")
    if hosted and channel in {"local", "chat"}:
        raise ConfigurationError("Hosted deployments require GUAVA_CHANNEL=phone or webrtc")
    number = os.environ.get("GUAVA_AGENT_NUMBER", "").strip()
    if channel == "phone" and not re.fullmatch(r"\+[1-9]\d{1,14}", number):
        raise ConfigurationError("GUAVA_AGENT_NUMBER must be an E.164 phone number")
    agent = create_agent()
    if channel == "local":
        agent.call_local()
    elif channel == "chat":
        agent.chat()
    elif channel == "webrtc":
        agent.listen_webrtc()
    elif channel == "phone":
        agent.listen_phone(number)


def entrypoint() -> int:
    configure_logging()
    try:
        run()
    except ConfigurationError as exc:
        logger.error("%s", exc)
        return 1
    except Exception as exc:
        logger.error("Runtime stopped (%s). Raw request details withheld.", type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(entrypoint())
