import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

bot_engine_pkg = types.ModuleType("bot_engine")
sys.modules.setdefault("bot_engine", bot_engine_pkg)
sys.modules["bot_engine.mcm_core_engine"] = importlib.import_module("mcm_core_engine")
sys.modules["bot_engine.strukture_engine"] = importlib.import_module("strukture_engine")
setattr(bot_engine_pkg, "mcm_core_engine", sys.modules["bot_engine.mcm_core_engine"])
setattr(bot_engine_pkg, "strukture_engine", sys.modules["bot_engine.strukture_engine"])

import bot_gate_funktions as gate_module


class BotStub:
    pass


class BotGateFunktionsTests(unittest.TestCase):

    def test_evaluate_entry_decision_uses_runtime_result_and_keeps_state_blocks(self):
        original_runtime = gate_module.build_runtime_entry_decision
        original_brain = gate_module.decide_mcm_brain_entry
        original_debug = gate_module.DEBUG

        calls = {"brain_calls": 0}

        def fake_runtime(window, candle_state, bot=None):
            return {
                "decision": "LONG",
                "entry_price": 100.0,
                "tp_price": 104.0,
                "sl_price": 98.0,
                "rr_value": 2.0,
                "energy": 0.77,
                "coherence": 0.41,
                "asymmetry": 1,
                "coh_zone": 1.0,
                "self_state": "stable",
                "attractor": "cooperate",
                "memory_center": 0.28,
                "memory_strength": 5,
                "vision": {"left_eye_field": 0.22},
                "filtered_vision": {"target_map": 0.61},
                "focus": {"focus_confidence": 0.66, "target_lock": 0.49},
                "world_state": {"tension_state": {"energy": 0.77}},
                "structure_perception_state": {"structure_quality": 0.81},
                "outer_visual_perception_state": {"signal_relevance": 0.58},
                "inner_field_perception_state": {"field_mean_energy": 0.31},
                "processing_state": {"processing_readiness": 0.73},
                "perception_state": {"structure_quality": 0.81},
                "felt_state": {"pressure": 0.19},
                "thought_state": {"maturity": 0.57},
                "meta_regulation_state": {"decision": "LONG", "allow_plan": True},
                "expectation_state": {"entry_expectation": 0.62, "target_expectation": 0.54},
                "state_signature": {"signature_key": "sig_runtime"},
                "entry_validity_band": {"lower": 99.5, "upper": 100.5},
                "target_conviction": 0.63,
                "risk_model_score": 0.38,
                "reward_model_score": 0.71,
                "signature_bias": 0.12,
                "signature_block": False,
                "signature_quality": 0.59,
                "signature_distance": 0.08,
                "context_cluster_id": "ctx_7",
                "context_cluster_bias": 0.14,
                "context_cluster_quality": 0.69,
                "context_cluster_distance": 0.11,
                "context_cluster_block": False,
                "inhibition_level": 0.09,
                "habituation_level": 0.04,
                "competition_bias": -0.03,
                "observation_mode": False,
                "long_score": 1.18,
                "short_score": -0.26,
            }

        def fake_brain(window, candle_state, bot=None):
            calls["brain_calls"] += 1
            return None

        try:
            gate_module.build_runtime_entry_decision = fake_runtime
            gate_module.decide_mcm_brain_entry = fake_brain
            gate_module.DEBUG = False

            result = gate_module.evaluate_entry_decision(
                BotStub(),
                [{"timestamp": 1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0}],
                {"close": 100.5},
            )

            self.assertEqual(calls["brain_calls"], 0)
            self.assertEqual(result.get("decision"), "LONG")
            self.assertEqual(float(result.get("rr_value", 0.0)), 2.0)
            self.assertEqual(result.get("world_state", {}).get("tension_state", {}).get("energy"), 0.77)
            self.assertEqual(result.get("structure_perception_state", {}).get("structure_quality"), 0.81)
            self.assertEqual(result.get("outer_visual_perception_state", {}).get("signal_relevance"), 0.58)
            self.assertEqual(result.get("inner_field_perception_state", {}).get("field_mean_energy"), 0.31)
            self.assertEqual(result.get("processing_state", {}).get("processing_readiness"), 0.73)
            self.assertEqual(result.get("perception_state", {}).get("structure_quality"), 0.81)
            self.assertEqual(result.get("felt_state", {}).get("pressure"), 0.19)
            self.assertEqual(result.get("thought_state", {}).get("maturity"), 0.57)
            self.assertEqual(result.get("meta_regulation_state", {}).get("decision"), "LONG")
            self.assertEqual(result.get("expectation_state", {}).get("entry_expectation"), 0.62)
            self.assertEqual(result.get("state_signature", {}).get("signature_key"), "sig_runtime")
            self.assertEqual(result.get("context_cluster_id"), "ctx_7")
        finally:
            gate_module.build_runtime_entry_decision = original_runtime
            gate_module.decide_mcm_brain_entry = original_brain
            gate_module.DEBUG = original_debug

    def test_evaluate_entry_decision_falls_back_to_brain_when_runtime_returns_none(self):
        original_runtime = gate_module.build_runtime_entry_decision
        original_brain = gate_module.decide_mcm_brain_entry
        original_debug = gate_module.DEBUG

        calls = {"brain_calls": 0}

        def fake_runtime(window, candle_state, bot=None):
            return None

        def fake_brain(window, candle_state, bot=None):
            calls["brain_calls"] += 1
            return {
                "decision": "SHORT",
                "entry_price": 100.0,
                "tp_price": 96.0,
                "sl_price": 102.0,
                "rr_value": 0.0,
                "energy": 0.66,
                "coherence": -0.37,
                "asymmetry": -1,
                "coh_zone": -1.0,
                "self_state": "active",
                "attractor": "analysis",
                "memory_center": -0.21,
                "memory_strength": 4,
                "vision": {"left_eye_field": -0.18},
                "filtered_vision": {"threat_map": 0.44},
                "focus": {"focus_confidence": 0.41, "target_lock": 0.23},
                "world_state": {"tension_state": {"coherence": -0.37}},
                "structure_perception_state": {"structure_quality": 0.58},
                "outer_visual_perception_state": {"signal_relevance": 0.33},
                "inner_field_perception_state": {"field_mean_risk": -0.29},
                "processing_state": {"processing_load": 0.46},
                "perception_state": {"novelty_score": 0.27},
                "felt_state": {"risk": 0.61},
                "thought_state": {"uncertainty": 0.48},
                "meta_regulation_state": {"decision": "SHORT", "allow_plan": True},
                "expectation_state": {"entry_expectation": 0.43},
                "state_signature": {"signature_key": "sig_fallback"},
                "entry_validity_band": {"lower": 99.7, "upper": 100.3},
                "target_conviction": 0.47,
                "risk_model_score": 0.55,
                "reward_model_score": 0.44,
                "signature_bias": -0.11,
                "signature_block": False,
                "signature_quality": 0.52,
                "signature_distance": 0.09,
                "context_cluster_id": "ctx_3",
                "context_cluster_bias": -0.13,
                "context_cluster_quality": 0.57,
                "context_cluster_distance": 0.15,
                "context_cluster_block": False,
                "inhibition_level": 0.17,
                "habituation_level": 0.05,
                "competition_bias": -0.12,
                "observation_mode": False,
                "long_score": -0.31,
                "short_score": 0.96,
            }

        try:
            gate_module.build_runtime_entry_decision = fake_runtime
            gate_module.decide_mcm_brain_entry = fake_brain
            gate_module.DEBUG = False

            result = gate_module.evaluate_entry_decision(
                BotStub(),
                [{"timestamp": 2, "open": 100.0, "high": 101.0, "low": 98.0, "close": 99.0, "volume": 11.0}],
                {"close": 99.0},
            )

            self.assertEqual(calls["brain_calls"], 1)
            self.assertEqual(result.get("decision"), "SHORT")
            self.assertAlmostEqual(float(result.get("rr_value", 0.0)), 2.0, places=6)
            self.assertEqual(result.get("state_signature", {}).get("signature_key"), "sig_fallback")
            self.assertEqual(result.get("meta_regulation_state", {}).get("decision"), "SHORT")
            self.assertEqual(result.get("context_cluster_id"), "ctx_3")
            self.assertAlmostEqual(float(result.get("short_score", 0.0)), 0.96, places=6)
        finally:
            gate_module.build_runtime_entry_decision = original_runtime
            gate_module.decide_mcm_brain_entry = original_brain
            gate_module.DEBUG = original_debug


if __name__ == "__main__":
    unittest.main()