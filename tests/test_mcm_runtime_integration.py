import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import MCM_Brain_Modell as brain


class BotStub:
    def __init__(self):
        self.position = None
        self.pending_entry = {"side": "LONG"}
        self.current_timestamp = None
        self.mcm_brain = None
        self.mcm_snapshot = {}
        self.mcm_last_action = "stable"
        self.mcm_last_attractor = "neutral"
        self.mcm_runtime_snapshot = {}
        self.mcm_runtime_decision_state = {}
        self.mcm_runtime_market_ticks = 0
        self.mcm_decision_episode = {}
        self.mcm_experience_space = {}
        self.mcm_last_observe_timestamp = None
        self.mcm_episode_seq = 0
        self.expectation_state = {}
        self.structure_perception_state = {}
        self.outer_visual_perception_state = {}
        self.inner_field_perception_state = {}
        self.processing_state = {}
        self.perception_state = {}
        self.felt_state = {}
        self.thought_state = {}
        self.meta_regulation_state = {"decision": "WAIT"}
        self.last_signature_context = {}
        self.focus_point = 0.0
        self.focus_confidence = 0.22
        self.target_lock = 0.15
        self.last_signal_relevance = 0.11
        self.inhibition_level = 0.09
        self.habituation_level = 0.04
        self.competition_bias = -0.03
        self.observation_mode = True


class MCMRuntimeIntegrationTests(unittest.TestCase):
    def test_step_runtime_builds_hold_state_during_pending_entry(self):
        bot = BotStub()
        window = [
            {"timestamp": 1, "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.4, "volume": 10.0},
            {"timestamp": 2, "open": 100.4, "high": 101.3, "low": 100.1, "close": 100.9, "volume": 11.0},
        ]

        runtime_result = brain.step_mcm_runtime(window, {"close": 100.9}, bot=bot)
        entry_result = brain.build_runtime_entry_decision(window, {"close": 100.9}, bot=bot)

        self.assertEqual(runtime_result.get("decision"), "WAIT")
        self.assertEqual(runtime_result.get("decision_tendency"), "observe")
        self.assertEqual(runtime_result.get("rejection_reason"), "runtime_active_trade")
        self.assertEqual(bot.mcm_runtime_snapshot.get("timestamp"), 2)
        self.assertEqual(bot.mcm_runtime_snapshot.get("decision_tendency"), "observe")
        self.assertEqual(bot.mcm_runtime_decision_state.get("proposed_decision"), "WAIT")
        self.assertEqual(bot.mcm_last_observe_timestamp, 2)
        self.assertEqual(entry_result.get("decision"), "WAIT")
        self.assertEqual(entry_result.get("rejection_reason"), "runtime_active_trade")

    def test_mark_runtime_episode_event_updates_episode_and_experience_space(self):
        bot = BotStub()
        bot.current_timestamp = 7

        brain.mark_runtime_episode_event(
            bot,
            "submitted",
            {"reason": "long"},
        )

        self.assertEqual(bot.mcm_decision_episode.get("action_status"), "submitted")
        self.assertEqual(bot.mcm_decision_episode.get("lifecycle_state"), "submitted")
        self.assertEqual(bot.mcm_decision_episode.get("last_event"), "submitted")
        self.assertEqual(len(bot.mcm_decision_episode.get("events", [])), 1)
        self.assertEqual(int(bot.mcm_experience_space.get("event_submitted", 0)), 1)
        self.assertEqual(bot.mcm_experience_space.get("last_event"), "submitted")


if __name__ == "__main__":
    unittest.main()