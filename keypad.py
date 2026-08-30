"""Keypad (DTMF) control routing for Second Draft.

Pure routing only: map (stage, digit) to a KeypadAction. No call/session state
lives here — the Controller in adaptive.py owns the state machine and wires
actions to it (PAUSE -> _pause, RETRY -> replay, END -> _finish).

Accepts both vocabularies:
  - Controller modes (adaptive_models.Mode values): coach, rehearsal, safety, ended
  - the original handoff stages: intake, rehearsal, debrief, do_over, takeaway,
    safety_exit, ended

Control scheme (speech remains the main interface — no phone-tree menus):
  0  leave roleplay and return to the coach        -> PAUSE
  1  retry / replay the scene                      -> RETRY
  9  end the call                                  -> END
  *  briefly explain the controls, no mode change  -> HELP
  anything else                                    -> IGNORE
"""

from enum import Enum


class KeypadAction(str, Enum):
    PAUSE = "pause"
    RETRY = "retry"
    END = "end"
    HELP = "help"
    IGNORE = "ignore"


# States where the caller is inside a roleplay scene that 0 can leave.
_PAUSE_STATES = frozenset({"rehearsal", "do_over"})

# States where 1 replays the scene: the post-scene debrief (old vocabulary)
# or coach mode (new vocabulary — the Controller's replay() re-checks that a
# saved moment exists and that the session is not in safety/ended).
_RETRY_STATES = frozenset({"debrief", "coach"})

# Safety states: only ending the call or hearing the controls is allowed.
_SAFETY_STATES = frozenset({"safety", "safety_exit"})

_ACTIVE_STATES = (
    _PAUSE_STATES | _RETRY_STATES | _SAFETY_STATES | frozenset({"intake", "takeaway"})
)

STAGES = _ACTIVE_STATES | frozenset({"ended"})


def route_key(stage: str, digit: str) -> KeypadAction:
    """Route a single DTMF digit pressed during `stage` to a control action.

    Safety invariants:
      - In a safety state, no key resumes or restarts roleplay; only ending
        the call (9) or hearing the controls (*) is allowed.
      - Once the call has ended, every key is ignored.
      - An unknown stage is treated as unsafe: every key is ignored rather
        than acting in a state we don't recognize.
    """
    if stage not in _ACTIVE_STATES:
        return KeypadAction.IGNORE

    if digit == "9":
        return KeypadAction.END
    if digit == "*":
        return KeypadAction.HELP

    if stage in _SAFETY_STATES:
        return KeypadAction.IGNORE

    if digit == "0" and stage in _PAUSE_STATES:
        return KeypadAction.PAUSE
    if digit == "1" and stage in _RETRY_STATES:
        return KeypadAction.RETRY

    return KeypadAction.IGNORE
