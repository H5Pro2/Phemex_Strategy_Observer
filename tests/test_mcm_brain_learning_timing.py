import copy
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

import MCM_Brain_Modell as brain


class BotStub:
    def __init__(self):
        self.signature_memory = {}
        self.last_signature_key = None
        self.last_signature_outcome = None
        self.last_signature_context = None
        self.context_clusters = {}
        self.context_cluster_seq = 0
        self.last_context_cluster_id = None
        self.last_context_cluster_key = None


class MCMLearningTimingTests(unittest.TestCase):
    def test_register_pending_learning_context_does_not_mutate_signature_or_cluster_memory(self):
        bot = BotStub()
        bot.signature_memory = {
            "sig_old": {
                "seen": 3,
                "tp": 2,
                "sl": 1,
                "cancel": 0,
                "timeout": 0,
                "score": 1.4,
                "last_outcome": "tp_hit",
                "age": 4,
                "signature_vector": [0.2] * 26,
            }
        }
        bot.context_clusters = {
            "ctx_1": {
                "cluster_id": "ctx_1",
                "center_vector": [0.2] * 26,
                "variance": 0.01,
                "radius": 0.02,
                "seen": 5,
                "tp": 3,
                "sl": 2,
                "cancel": 0,
                "timeout": 0,
                "score": 1.2,
                "trust": 0.55,
                "age": 2,
                "signature_keys": ["sig_old"],
                "last_signature_key": "sig_old",
                "last_outcome": "tp_hit",
                "last_distance": 0.01,
            }
        }
        bot.context_cluster_seq = 1

        signature_before = copy.deepcopy(bot.signature_memory)
        clusters_before = copy.deepcopy(bot.context_clusters)

        result = brain.register_pending_learning_context(
            bot,
            {
                "signature_key": "sig_new",
                "signature_vector": [0.2] * 26,
            },
        )

        self.assertEqual(bot.signature_memory, signature_before)
        self.assertEqual(bot.context_clusters, clusters_before)
        self.assertEqual(bot.last_signature_key, "sig_new")
        self.assertEqual(bot.last_signature_context.get("signature_key"), "sig_new")
        self.assertEqual(bot.last_context_cluster_id, "ctx_1")
        self.assertEqual(result.get("context_cluster_id"), "ctx_1")

    def test_commit_pending_learning_context_updates_memory_only_after_outcome(self):
        bot = BotStub()

        brain.register_pending_learning_context(
            bot,
            {
                "signature_key": "sig_entry",
                "signature_vector": [0.11] * 26,
            },
        )

        self.assertEqual(bot.signature_memory, {})
        self.assertEqual(bot.context_clusters, {})

        result = brain.commit_pending_learning_context(
            bot,
            outcome="tp_hit",
        )

        self.assertEqual(bot.last_signature_key, "sig_entry")
        self.assertIn("sig_entry", bot.signature_memory)
        self.assertEqual(int(bot.signature_memory["sig_entry"].get("seen", 0)), 1)
        self.assertEqual(int(bot.signature_memory["sig_entry"].get("tp", 0)), 1)
        self.assertEqual(bot.signature_memory["sig_entry"].get("last_outcome"), "tp_hit")
        self.assertEqual(list(bot.signature_memory["sig_entry"].get("signature_vector", [])), [0.11] * 26)

        cluster_id = str(result.get("context_cluster_id") or "")
        self.assertTrue(cluster_id)
        self.assertIn(cluster_id, bot.context_clusters)
        self.assertEqual(int(bot.context_clusters[cluster_id].get("seen", 0)), 1)
        self.assertEqual(int(bot.context_clusters[cluster_id].get("tp", 0)), 1)
        self.assertEqual(bot.context_clusters[cluster_id].get("last_outcome"), "tp_hit")


if __name__ == "__main__":
    unittest.main()