"""Tests for the Second Draft keypad router (pure routing, no call state)."""

import pytest

from keypad import STAGES, KeypadAction, route_key

ALL_DIGITS = [str(n) for n in range(10)] + ["*", "#", "A", "B", "C", "D"]
ACTIVE_STAGES = sorted(STAGES - {"ended"})
CONTROL_DIGITS = {"0", "1", "9", "*"}
ROLEPLAY_STAGES = frozenset({"rehearsal", "do_over"})
RETRY_STAGES = frozenset({"debrief", "coach"})
SAFETY_STAGES = frozenset({"safety", "safety_exit"})


# --- 9: end the call ---------------------------------------------------------


@pytest.mark.parametrize("stage", ACTIVE_STAGES)
def test_nine_ends_call_from_every_active_stage(stage):
    assert route_key(stage, "9") is KeypadAction.END


def test_nine_ignored_after_call_ended():
    assert route_key("ended", "9") is KeypadAction.IGNORE


# --- *: explain controls -----------------------------------------------------


@pytest.mark.parametrize("stage", ACTIVE_STAGES)
def test_star_gives_help_from_every_active_stage(stage):
    assert route_key(stage, "*") is KeypadAction.HELP


def test_star_ignored_after_call_ended():
    assert route_key("ended", "*") is KeypadAction.IGNORE


# --- 0: leave roleplay, return to the coach ----------------------------------


@pytest.mark.parametrize("stage", sorted(ROLEPLAY_STAGES))
def test_zero_pauses_roleplay(stage):
    assert route_key(stage, "0") is KeypadAction.PAUSE


@pytest.mark.parametrize("stage", sorted(STAGES - ROLEPLAY_STAGES))
def test_zero_ignored_outside_roleplay(stage):
    assert route_key(stage, "0") is KeypadAction.IGNORE


# --- 1: retry the scene, only from the debrief -------------------------------


@pytest.mark.parametrize("stage", sorted(RETRY_STAGES))
def test_one_retries_from_debrief_or_coach(stage):
    assert route_key(stage, "1") is KeypadAction.RETRY


@pytest.mark.parametrize("stage", sorted(STAGES - RETRY_STAGES))
def test_one_ignored_outside_retry_states(stage):
    assert route_key(stage, "1") is KeypadAction.IGNORE


# --- invalid keys ------------------------------------------------------------


@pytest.mark.parametrize("stage", sorted(STAGES))
@pytest.mark.parametrize("digit", sorted(set(ALL_DIGITS) - CONTROL_DIGITS))
def test_non_control_keys_always_ignored(stage, digit):
    assert route_key(stage, digit) is KeypadAction.IGNORE


@pytest.mark.parametrize("digit", ["", "10", "99", "e", "star", None])
def test_malformed_digits_ignored(digit):
    assert route_key("rehearsal", digit) is KeypadAction.IGNORE


# --- repeated presses --------------------------------------------------------


@pytest.mark.parametrize(
    ("stage", "digit", "action"),
    [
        ("rehearsal", "0", KeypadAction.PAUSE),
        ("debrief", "1", KeypadAction.RETRY),
        ("intake", "9", KeypadAction.END),
        ("takeaway", "*", KeypadAction.HELP),
    ],
)
def test_repeated_presses_are_stable(stage, digit, action):
    # The router is pure: mashing a key yields the same action every time,
    # and the state machine in main.py decides what a repeat means.
    assert [route_key(stage, digit) for _ in range(5)] == [action] * 5


def test_zero_after_leaving_roleplay_is_ignored():
    # First 0 leaves the roleplay; once the stage has moved to debrief,
    # pressing 0 again does nothing.
    assert route_key("rehearsal", "0") is KeypadAction.PAUSE
    assert route_key("debrief", "0") is KeypadAction.IGNORE


# --- safety exit -------------------------------------------------------------


@pytest.mark.parametrize("stage", sorted(SAFETY_STAGES))
@pytest.mark.parametrize("digit", sorted(set(ALL_DIGITS) - {"9", "*"}))
def test_safety_states_block_everything_but_end_and_help(stage, digit):
    assert route_key(stage, digit) is KeypadAction.IGNORE


@pytest.mark.parametrize("stage", sorted(SAFETY_STAGES))
def test_safety_states_never_restart_roleplay(stage):
    for digit in ALL_DIGITS:
        assert route_key(stage, digit) not in (
            KeypadAction.PAUSE,
            KeypadAction.RETRY,
        )


@pytest.mark.parametrize("stage", sorted(SAFETY_STAGES))
def test_safety_states_still_allow_ending_and_help(stage):
    assert route_key(stage, "9") is KeypadAction.END
    assert route_key(stage, "*") is KeypadAction.HELP


# --- ended / unknown stages --------------------------------------------------


@pytest.mark.parametrize("digit", ALL_DIGITS)
def test_ended_ignores_every_key(digit):
    assert route_key("ended", digit) is KeypadAction.IGNORE


@pytest.mark.parametrize("stage", ["", "REHEARSAL", "paused", "unknown", None])
@pytest.mark.parametrize("digit", sorted(CONTROL_DIGITS))
def test_unknown_stage_ignores_every_key(stage, digit):
    assert route_key(stage, digit) is KeypadAction.IGNORE
