import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import bot_engine.mcm_core_engine as core


class MCMCoreEngineTests(unittest.TestCase):

    def _assert_state_bounds(self, state):
        self.assertGreaterEqual(float(state.get("coherence", 0.0)), -1.0)
        self.assertLessEqual(float(state.get("coherence", 0.0)), 1.0)
        self.assertIn(int(state.get("asymmetry", 0)), (-1, 0, 1))
        self.assertGreaterEqual(float(state.get("stability", 0.0)), 0.0)
        self.assertLessEqual(float(state.get("stability", 0.0)), 1.0)
        self.assertGreaterEqual(float(state.get("perceived_pressure", 0.0)), 0.0)
        self.assertLessEqual(float(state.get("perceived_pressure", 0.0)), 1.0)
        self.assertGreaterEqual(float(state.get("volume_pressure", 0.0)), -1.0)
        self.assertLessEqual(float(state.get("volume_pressure", 0.0)), 1.0)
        self.assertGreaterEqual(float(state.get("relative_range", 0.0)), 0.0)
        self.assertLessEqual(float(state.get("relative_range", 0.0)), 1.5)

    def test_build_tension_state_from_window_returns_zero_state_for_empty_window(self):
        state = core.build_tension_state_from_window([])

        self.assertEqual(
            state,
            {
                "energy": 0.0,
                "coherence": 0.0,
                "asymmetry": 0,
                "coh_zone": 0.0,
                "relative_range": 0.0,
                "momentum": 0.0,
                "stability": 0.0,
                "perceived_pressure": 0.0,
                "volume_pressure": 0.0,
            },
        )

    def test_build_tension_state_from_window_returns_bounded_bullish_state(self):
        window = [
            {"open": 100.0, "high": 101.0, "low": 99.6, "close": 100.4, "volume": 8.0},
            {"open": 100.4, "high": 101.2, "low": 100.1, "close": 100.9, "volume": 9.0},
            {"open": 100.9, "high": 101.5, "low": 100.6, "close": 101.1, "volume": 10.0},
            {"open": 101.1, "high": 101.8, "low": 100.8, "close": 101.4, "volume": 11.0},
            {"open": 101.4, "high": 102.0, "low": 101.0, "close": 101.6, "volume": 12.0},
            {"open": 101.6, "high": 102.2, "low": 101.3, "close": 101.9, "volume": 12.0},
            {"open": 101.9, "high": 102.5, "low": 101.6, "close": 102.1, "volume": 13.0},
            {"open": 102.1, "high": 102.9, "low": 101.9, "close": 102.7, "volume": 15.0},
        ]

        state = core.build_tension_state_from_window(window)

        self._assert_state_bounds(state)
        self.assertGreater(float(state.get("energy", 0.0)), 0.0)
        self.assertEqual(int(state.get("asymmetry", 0)), 1)
        self.assertGreater(float(state.get("momentum", 0.0)), 0.0)

    def test_build_tension_state_from_window_returns_bounded_bearish_state(self):
        window = [
            {"open": 102.8, "high": 103.0, "low": 102.1, "close": 102.4, "volume": 9.0},
            {"open": 102.4, "high": 102.7, "low": 101.8, "close": 102.0, "volume": 10.0},
            {"open": 102.0, "high": 102.2, "low": 101.3, "close": 101.6, "volume": 11.0},
            {"open": 101.6, "high": 101.9, "low": 101.0, "close": 101.2, "volume": 12.0},
            {"open": 101.2, "high": 101.5, "low": 100.5, "close": 100.8, "volume": 13.0},
            {"open": 100.8, "high": 101.0, "low": 100.0, "close": 100.4, "volume": 12.0},
            {"open": 100.4, "high": 100.7, "low": 99.7, "close": 100.0, "volume": 14.0},
            {"open": 100.0, "high": 100.2, "low": 99.1, "close": 99.3, "volume": 16.0},
        ]

        state = core.build_tension_state_from_window(window)

        self._assert_state_bounds(state)
        self.assertGreater(float(state.get("energy", 0.0)), 0.0)
        self.assertEqual(int(state.get("asymmetry", 0)), -1)
        self.assertLess(float(state.get("momentum", 0.0)), 0.0)


if __name__ == "__main__":
    unittest.main()