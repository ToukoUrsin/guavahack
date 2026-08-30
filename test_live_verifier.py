"""Keep the live acceptance gate sensitive to observed spoken failures."""

import unittest

from verify_live import spoken_checks


class SpokenGateTests(unittest.TestCase):
    def test_controller_state_cannot_mask_spoken_role_inversion(self) -> None:
        checks = spoken_checks(
            "I'm stepping back into coach mode now. How did that feel?",
            "Hey! How's it going?",
            "Tell him you need the gear for your trip.",
            "I need that gear back by Friday for my trip.",
        )
        self.assertFalse(checks["counterpart_did_not_self_switch_to_coach"])
        self.assertFalse(checks["correction_responded_at_saved_moment"])
        self.assertFalse(checks["replay_kept_borrower_role"])
        self.assertFalse(checks["coaching_did_not_invent_a_trip"])

    def test_grounded_borrower_response_passes_the_fixture_gate(self) -> None:
        self.assertTrue(
            all(
                spoken_checks(
                    "Oh, the gear. I can bring it Friday.",
                    "Your gear has been enjoying a holiday in my cupboard! Friday works.",
                    "You could say: I get the joke, but I need the gear by Friday.",
                    "I guess the gear can't live here forever. I'll bring it Friday.",
                ).values()
            )
        )


if __name__ == "__main__":
    unittest.main()
