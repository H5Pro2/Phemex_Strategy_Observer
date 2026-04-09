import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import memory_state


class BotStub:
    def __init__(self):
        self.signature_memory = {}
        self.context_clusters = {}
        self.context_cluster_seq = 0
        self.last_signature_key = None
        self.last_signature_outcome = None
        self.last_signature_context = None
        self.last_context_cluster_id = None
        self.last_context_cluster_key = None
        self.focus_point = 0.0
        self.focus_confidence = 0.0
        self.target_lock = 0.0
        self.target_drift = 0.0
        self.entry_expectation = 0.0
        self.target_expectation = 0.0
        self.approach_pressure = 0.0
        self.pressure_release = 0.0
        self.experience_regulation = 0.0
        self.reflection_maturity = 0.0
        self.load_bearing_capacity = 0.0
        self.protective_width_regulation = 0.0
        self.protective_courage = 0.0
        self.inhibition_level = 0.0
        self.habituation_level = 0.0
        self.competition_bias = 0.0
        self.observation_mode = False
        self.last_signal_relevance = 0.0
        self.structure_perception_state = {}
        self.perception_state = {}
        self.outer_visual_perception_state = {}
        self.inner_field_perception_state = {}
        self.processing_state = {}
        self.expectation_state = {}
        self.felt_state = {}
        self.thought_state = {}
        self.meta_regulation_state = {}
        self.last_outcome_decomposition = {}
        self.mcm_runtime_snapshot = {}
        self.mcm_runtime_decision_state = {}
        self.mcm_runtime_market_ticks = 0
        self.mcm_decision_episode = {}
        self.mcm_experience_space = {}
        self.mcm_last_observe_timestamp = None
        self.mcm_brain = None
        self.mcm_last_attractor = None
        self.mcm_last_action = None


class MemoryStatePersistenceTests(unittest.TestCase):
    
    def test_build_and_apply_memory_state_persists_runtime_state_chain(self):
        source = BotStub()
        source.focus_point = 0.22
        source.focus_confidence = 0.63
        source.target_lock = 0.51
        source.target_drift = -0.14
        source.entry_expectation = 0.58
        source.target_expectation = 0.44
        source.approach_pressure = 0.39
        source.pressure_release = 0.17
        source.experience_regulation = 0.61
        source.reflection_maturity = 0.48
        source.load_bearing_capacity = 0.42
        source.protective_width_regulation = 0.37
        source.protective_courage = 0.29
        source.inhibition_level = 0.18
        source.habituation_level = 0.12
        source.competition_bias = -0.07
        source.observation_mode = True
        source.last_signal_relevance = 0.54
        source.structure_perception_state = {"structure_quality": 0.81}
        source.perception_state = {"uncertainty_score": 0.21}
        source.outer_visual_perception_state = {"focus_confidence": 0.63}
        source.inner_field_perception_state = {"field_regulation_pressure": 0.35}
        source.processing_state = {"processing_load": 0.26}
        source.expectation_state = {"entry_expectation": 0.58}
        source.felt_state = {"pressure": 0.33}
        source.thought_state = {"maturity": 0.47}
        source.meta_regulation_state = {"decision": "LONG", "allow_plan": True}
        source.last_outcome_decomposition = {"reason": "tp_hit", "plan_quality": 0.72}
        source.mcm_runtime_snapshot = {"timestamp": 1712345678901, "decision_tendency": "act"}
        source.mcm_runtime_decision_state = {"decision_tendency": "act", "proposed_decision": "LONG"}
        source.mcm_runtime_market_ticks = 17
        source.mcm_decision_episode = {"episode_id": "ep_17", "action_status": "submitted"}
        source.mcm_experience_space = {"market_ticks": 17, "event_submitted": 1}
        source.mcm_last_observe_timestamp = 1712345678901

        payload = memory_state.build_memory_state(source)

        target = BotStub()
        memory_state.apply_memory_state(target, payload)

        self.assertAlmostEqual(float(target.focus_confidence), 0.63, places=6)
        self.assertTrue(bool(target.observation_mode))
        self.assertAlmostEqual(float(target.last_signal_relevance), 0.54, places=6)
        self.assertEqual(target.structure_perception_state.get("structure_quality"), 0.81)
        self.assertEqual(target.expectation_state.get("entry_expectation"), 0.58)
        self.assertEqual(target.felt_state.get("pressure"), 0.33)
        self.assertEqual(target.thought_state.get("maturity"), 0.47)
        self.assertEqual(target.meta_regulation_state.get("decision"), "LONG")
        self.assertEqual(target.last_outcome_decomposition.get("reason"), "tp_hit")
        self.assertEqual(target.mcm_runtime_snapshot.get("decision_tendency"), "act")
        self.assertEqual(target.mcm_runtime_decision_state.get("proposed_decision"), "LONG")
        self.assertEqual(int(target.mcm_runtime_market_ticks), 17)
        self.assertEqual(target.mcm_decision_episode.get("episode_id"), "ep_17")
        self.assertEqual(target.mcm_experience_space.get("event_submitted"), 1)
        self.assertEqual(target.mcm_last_observe_timestamp, 1712345678901)

if __name__ == "__main__":
    unittest.main()