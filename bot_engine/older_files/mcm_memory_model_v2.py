# ==================================================
# mcm_memory_model_v2.py
# Meta-Speicher + Vektorraum Memory Model
# baut auf aktueller Bot-Zustandslogik auf
# ==================================================

import json
import math
import os
import random
from typing import Any, Dict, List, Optional

from config import Config


# ==================================================
# NODE
# ==================================================
class MetaRegimeNode:

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(
        self,
        node_id: int,
        center: List[float],
        spread: Optional[List[float]] = None,
        visits: int = 1,
        side_stats: Optional[Dict[str, Dict[str, Any]]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):

        self.node_id = int(node_id)
        self.center = [float(x) for x in center]
        self.spread = [float(x) for x in (spread or [0.05] * len(self.center))]
        self.visits = int(visits)

        self.side_stats = side_stats or self._default_side_stats()
        self.meta = meta or self._default_meta()

        for side_key in ("LONG", "SHORT"):
            self.side_stats.setdefault(side_key, {})
            defaults = self._default_side_stats()[side_key]
            for key, value in defaults.items():
                self.side_stats[side_key].setdefault(key, value)

        for key, value in self._default_meta().items():
            self.meta.setdefault(key, value)

    # --------------------------------------------------
    # DEFAULT SIDE STATS
    # --------------------------------------------------
    @staticmethod
    def _default_side_stats() -> Dict[str, Dict[str, Any]]:
        return {
            "LONG": {
                "tp": 0,
                "sl": 0,
                "cancel": 0,
                "no_fill": 0,
                "market_shift": 0,
                "rr_sum": 0.0,
                "rr_count": 0,
                "entry_shift_sum": 0.0,
                "entry_shift_count": 0,
                "entry_quality_sum": 0.0,
                "entry_quality_count": 0,
                "entry_distance_sum": 0.0,
                "entry_distance_count": 0,
                "risk_sum": 0.0,
                "risk_count": 0,
                "reward_sum": 0.0,
                "reward_count": 0,
                "hold_bars_sum": 0.0,
                "hold_bars_count": 0,
                "score_sum": 0.0,
                "score_count": 0,
            },
            "SHORT": {
                "tp": 0,
                "sl": 0,
                "cancel": 0,
                "no_fill": 0,
                "market_shift": 0,
                "rr_sum": 0.0,
                "rr_count": 0,
                "entry_shift_sum": 0.0,
                "entry_shift_count": 0,
                "entry_quality_sum": 0.0,
                "entry_quality_count": 0,
                "entry_distance_sum": 0.0,
                "entry_distance_count": 0,
                "risk_sum": 0.0,
                "risk_count": 0,
                "reward_sum": 0.0,
                "reward_count": 0,
                "hold_bars_sum": 0.0,
                "hold_bars_count": 0,
                "score_sum": 0.0,
                "score_count": 0,
            },
        }

    # --------------------------------------------------
    # DEFAULT META
    # --------------------------------------------------
    @staticmethod
    def _default_meta() -> Dict[str, Any]:
        return {
            "activation": 1.0,
            "stability": 0.5,
            "quality": 0.0,
            "novelty": 1.0,
            "last_seen_ts": None,
            "first_seen_ts": None,
            "merge_count": 0,
            "match_count": 0,
            "miss_count": 0,
        }

    # --------------------------------------------------
    # DISTANCE
    # --------------------------------------------------
    def distance(self, vector: List[float], weights: Optional[List[float]] = None) -> float:

        if not vector:
            return 999999.0

        m = min(len(self.center), len(vector))
        score = 0.0

        for i in range(m):
            w = float(weights[i]) if weights and i < len(weights) else 1.0
            scale = max(float(self.spread[i]) if i < len(self.spread) else 0.05, 1e-6)
            delta = (float(self.center[i]) - float(vector[i])) / scale
            score += (delta * delta) * w

        return float(math.sqrt(score))

    # --------------------------------------------------
    # ADAPT
    # --------------------------------------------------
    def adapt(self, vector: List[float], timestamp=None, lr: float = 0.08):

        self.visits += 1
        self.meta["match_count"] = int(self.meta.get("match_count", 0) or 0) + 1
        self.meta["activation"] = min(3.0, float(self.meta.get("activation", 1.0) or 1.0) + 0.02)
        self.meta["novelty"] = max(0.0, float(self.meta.get("novelty", 1.0) or 1.0) - 0.01)
        self.meta["last_seen_ts"] = timestamp

        if self.meta.get("first_seen_ts") is None:
            self.meta["first_seen_ts"] = timestamp

        limit = min(len(self.center), len(vector))

        for i in range(limit):
            old_value = float(self.center[i])
            new_value = float(vector[i])
            delta = new_value - old_value

            self.center[i] = old_value + (lr * delta)

            old_spread = float(self.spread[i]) if i < len(self.spread) else 0.05
            updated_spread = (old_spread * 0.92) + (abs(delta) * 0.08)

            if i < len(self.spread):
                self.spread[i] = max(0.02, min(updated_spread, 3.0))

        self._refresh_meta_quality()

    # --------------------------------------------------
    # REFRESH META QUALITY
    # --------------------------------------------------
    def _refresh_meta_quality(self):

        total_wins = int(self.side_stats["LONG"].get("tp", 0) or 0) + int(self.side_stats["SHORT"].get("tp", 0) or 0)
        total_losses = int(self.side_stats["LONG"].get("sl", 0) or 0) + int(self.side_stats["SHORT"].get("sl", 0) or 0)
        total_noise = (
            int(self.side_stats["LONG"].get("cancel", 0) or 0)
            + int(self.side_stats["LONG"].get("no_fill", 0) or 0)
            + int(self.side_stats["LONG"].get("market_shift", 0) or 0)
            + int(self.side_stats["SHORT"].get("cancel", 0) or 0)
            + int(self.side_stats["SHORT"].get("no_fill", 0) or 0)
            + int(self.side_stats["SHORT"].get("market_shift", 0) or 0)
        )

        total = total_wins + total_losses + total_noise

        if total <= 0:
            self.meta["quality"] = 0.0
            self.meta["stability"] = min(1.0, 0.2 + (self.visits / 50.0))
            return

        quality = (total_wins - total_losses - (0.5 * total_noise)) / max(total, 1)
        stability = min(1.0, (self.visits / 40.0) + (max(total_wins, 0) / max(total, 1)) * 0.5)

        self.meta["quality"] = float(max(-1.0, min(1.0, quality)))
        self.meta["stability"] = float(max(0.0, min(1.0, stability)))

    # --------------------------------------------------
    # SIDE_SCORE
    # --------------------------------------------------
    def side_score(self, side: str) -> float:

        side_key = str(side).upper().strip()
        if side_key not in ("LONG", "SHORT"):
            return 0.0

        stats = self.side_stats.get(side_key, {})

        tp = int(stats.get("tp", 0) or 0)
        sl = int(stats.get("sl", 0) or 0)
        cancel = int(stats.get("cancel", 0) or 0)
        no_fill = int(stats.get("no_fill", 0) or 0)
        market_shift = int(stats.get("market_shift", 0) or 0)

        rr_sum = float(stats.get("rr_sum", 0.0) or 0.0)
        rr_count = int(stats.get("rr_count", 0) or 0)
        entry_quality_sum = float(stats.get("entry_quality_sum", 0.0) or 0.0)
        entry_quality_count = int(stats.get("entry_quality_count", 0) or 0)

        total = tp + sl + cancel + no_fill + market_shift
        winrate = (tp / (tp + sl)) if (tp + sl) > 0 else 0.5
        avg_rr = (rr_sum / rr_count) if rr_count > 0 else float(getattr(Config, "RR", 2.0) or 2.0)
        avg_quality = (entry_quality_sum / entry_quality_count) if entry_quality_count > 0 else 0.0
        noise_penalty = (cancel + no_fill + market_shift) / max(total, 1)

        score = 0.0
        score += (winrate - 0.5) * 1.5
        score += (avg_rr - float(getattr(Config, "RR", 2.0) or 2.0)) * 0.35
        score += avg_quality * 0.25
        score -= noise_penalty * 0.75
        score += float(self.meta.get("quality", 0.0) or 0.0) * 0.4
        score += float(self.meta.get("stability", 0.0) or 0.0) * 0.2

        return float(score)

    # --------------------------------------------------
    # TO_DICT
    # --------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "center": self.center,
            "spread": self.spread,
            "visits": self.visits,
            "side_stats": self.side_stats,
            "meta": self.meta,
        }

    # --------------------------------------------------
    # FROM_DICT
    # --------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            node_id=data.get("node_id", 0),
            center=data.get("center", []),
            spread=data.get("spread"),
            visits=data.get("visits", 1),
            side_stats=data.get("side_stats"),
            meta=data.get("meta"),
        )


# ==================================================
# MEMORY
# ==================================================
class MCMMetaVectorMemory:

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(self, path: str = "bot_memory/mcm_meta_vector_memory.json"):

        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        self.sensory_buffer: List[Dict[str, Any]] = []
        self.episodes: List[Dict[str, Any]] = []
        self.regime_nodes: List[MetaRegimeNode] = []
        self.transition_graph: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.reward_traces: List[Dict[str, Any]] = []
        self.meta_index: Dict[str, Any] = {
            "total_states": 0,
            "total_episodes": 0,
            "total_transitions": 0,
            "last_outcome": None,
        }
        self.attractor_state = {
            "name": "neutral",
            "node_id": None,
        }

        self.max_buffer = 4000
        self.max_episodes = 1200
        self.max_reward_traces = 2000
        self.node_match_threshold = 6.2
        self.max_nodes_before_consolidation = 500
        self.consolidate_interval_states = 250
        self.next_node_id = 1
        self.last_node_id = None
        self.active_episode = None
        self._save_counter = 0
        self._save_interval = 500
        self._last_consolidate_state_count = 0
        self._node_map: Dict[int, MetaRegimeNode] = {}
        self._side_match_cache: Dict[str, Optional[MetaRegimeNode]] = {}

        self.vector_weights = [
            1.30,
            1.20,
            1.10,
            1.10,
            0.90,
            0.90,
            0.90,
            0.90,
            0.60,
            0.80,
            0.70,
            0.70,
            0.60,
            0.60,
            0.50,
            0.85,
            0.95,
            0.85,
            0.70,
            0.75,
        ]

        self._load()
        self._upgrade_memory_schema()
    # --------------------------------------------------
    # UPGRADE MEMORY SCHEMA
    # --------------------------------------------------
    def _upgrade_memory_schema(self):

        target_size = len(self.vector_weights)

        for node in self.regime_nodes:
            center_missing = max(0, target_size - len(node.center))
            spread_missing = max(0, target_size - len(node.spread))

            if center_missing > 0:
                node.center.extend([0.0] * center_missing)

            if spread_missing > 0:
                node.spread.extend([0.08] * spread_missing)

        upgraded_buffer = []

        for item in self.sensory_buffer:
            if not isinstance(item, dict):
                continue

            upgraded_buffer.append({
                "energy": self._safe_float(item.get("energy", 0.0)),
                "coherence": self._safe_float(item.get("coherence", 0.0)),
                "asymmetry": int(self._safe_float(item.get("asymmetry", 0.0))),
                "resonance": self._safe_float(item.get("resonance", 0.0)),
                "coh_zone": self._safe_float(item.get("coh_zone", 0.0)),
                "body_strength": self._safe_float(item.get("body_strength", 0.0)),
                "wick_bias": self._safe_float(item.get("wick_bias", 0.0)),
                "close_position": self._safe_float(item.get("close_position", 0.0)),
                "return_intensity": self._safe_float(item.get("return_intensity", 0.0)),
                "side": str(item.get("side", "NONE")),
                "timestamp": item.get("timestamp"),
            })

        self.sensory_buffer = upgraded_buffer[-self.max_buffer:]

    # --------------------------------------------------
    # REBUILD NODE MAP
    # --------------------------------------------------
    def _rebuild_node_map(self):

        self._node_map = {}

        for node in self.regime_nodes:
            self._node_map[int(node.node_id)] = node

    # --------------------------------------------------
    # INVALIDATE SIDE CACHE
    # --------------------------------------------------
    def _invalidate_side_cache(self):
        self._side_match_cache = {}

    # --------------------------------------------------
    # GET NODE BY ID
    # --------------------------------------------------
    def _get_node_by_id(self, node_id) -> Optional[MetaRegimeNode]:

        if node_id is None:
            return None

        try:
            return self._node_map.get(int(node_id))
        except Exception:
            return None

    # --------------------------------------------------
    # LOAD
    # --------------------------------------------------
    def _load(self):

        if not os.path.exists(self.path):
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.sensory_buffer = data.get("sensory_buffer", [])
            self.episodes = data.get("episodes", [])
            self.transition_graph = data.get("transition_graph", {})
            self.reward_traces = data.get("reward_traces", [])
            self.meta_index = data.get("meta_index", self.meta_index)
            self.attractor_state = data.get("attractor_state", self.attractor_state)
            self.next_node_id = int(data.get("next_node_id", 1) or 1)
            self.last_node_id = data.get("last_node_id")

            self.regime_nodes = [
                MetaRegimeNode.from_dict(item)
                for item in data.get("regime_nodes", [])
                if isinstance(item, dict)
            ]
            self._rebuild_node_map()
            self._invalidate_side_cache()

        except Exception:
            self.sensory_buffer = []
            self.episodes = []
            self.regime_nodes = []
            self.transition_graph = {}
            self.reward_traces = []
            self.meta_index = {
                "total_states": 0,
                "total_episodes": 0,
                "total_transitions": 0,
                "last_outcome": None,
            }
            self.attractor_state = {
                "name": "neutral",
                "node_id": None,
            }
            self.next_node_id = 1
            self.last_node_id = None
            self.active_episode = None

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------
    def _save(self):

        try:
            data = {
                "sensory_buffer": self.sensory_buffer,
                "episodes": self.episodes,
                "regime_nodes": [node.to_dict() for node in self.regime_nodes],
                "transition_graph": self.transition_graph,
                "reward_traces": self.reward_traces,
                "meta_index": self.meta_index,
                "attractor_state": self.attractor_state,
                "next_node_id": self.next_node_id,
                "last_node_id": self.last_node_id,
            }

            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))

            os.replace(tmp_path, self.path)

        except Exception:
            pass

    # --------------------------------------------------
    # SAFE FLOAT
    # --------------------------------------------------
    def _safe_float(self, value, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    # --------------------------------------------------
    # SIDE TO FLOAT
    # --------------------------------------------------
    def _side_to_float(self, side: str) -> float:
        side_key = str(side).upper().strip()
        if side_key == "LONG":
            return 1.0
        if side_key == "SHORT":
            return -1.0
        return 0.0

    # --------------------------------------------------
    # LAST BUFFER VALUE
    # --------------------------------------------------
    def _buffer_value(self, index_from_end: int, key: str, default: float = 0.0) -> float:

        if len(self.sensory_buffer) < index_from_end:
            return float(default)

        item = self.sensory_buffer[-index_from_end]
        return self._safe_float(item.get(key, default), default)

    # --------------------------------------------------
    # STATE VECTOR
    # --------------------------------------------------
    def _state_vector(self, state: Dict[str, Any]) -> List[float]:

        energy = self._safe_float(state.get("energy", 0.0))
        coherence = self._safe_float(state.get("coherence", 0.0))
        asymmetry = self._safe_float(state.get("asymmetry", 0.0))
        resonance = self._safe_float(state.get("resonance", 0.0))
        coh_zone = self._safe_float(state.get("coh_zone", 0.0))
        body_strength = self._safe_float(state.get("body_strength", 0.0))
        wick_bias = self._safe_float(state.get("wick_bias", 0.0))
        close_position = self._safe_float(state.get("close_position", 0.0))
        return_intensity = self._safe_float(state.get("return_intensity", 0.0))
        side = self._side_to_float(state.get("side", "NONE"))

        prev_energy = self._buffer_value(1, "energy", 0.0)
        prev_coherence = self._buffer_value(1, "coherence", 0.0)
        prev_asymmetry = self._buffer_value(1, "asymmetry", 0.0)
        prev_resonance = self._buffer_value(1, "resonance", 0.0)
        prev_body_strength = self._buffer_value(1, "body_strength", 0.0)
        prev_close_position = self._buffer_value(1, "close_position", 0.0)

        prev2_energy = self._buffer_value(2, "energy", 0.0)
        prev2_coherence = self._buffer_value(2, "coherence", 0.0)
        prev2_asymmetry = self._buffer_value(2, "asymmetry", 0.0)
        prev2_resonance = self._buffer_value(2, "resonance", 0.0)

        energy_gradient = energy - prev_energy
        coherence_gradient = coherence - prev_coherence
        asymmetry_gradient = asymmetry - prev_asymmetry
        resonance_gradient = resonance - prev_resonance
        body_strength_gradient = body_strength - prev_body_strength
        close_position_gradient = close_position - prev_close_position

        energy_trend = prev_energy - prev2_energy
        coherence_trend = prev_coherence - prev2_coherence
        asymmetry_trend = prev_asymmetry - prev2_asymmetry
        resonance_trend = prev_resonance - prev2_resonance

        energy_persistence = 0.0
        if energy > 0.0 and prev_energy > 0.0:
            energy_persistence = 1.0
        elif energy < 0.0 and prev_energy < 0.0:
            energy_persistence = -1.0

        resonance_persistence = 1.0 if resonance > 0.35 and prev_resonance > 0.35 else 0.0

        return [
            energy / 3.0,
            coherence,
            asymmetry / 3.0,
            resonance,
            energy_gradient / 2.0,
            coherence_gradient / 2.0,
            asymmetry_gradient / 3.0,
            resonance_gradient,
            energy_trend / 2.0,
            coherence_trend / 2.0,
            asymmetry_trend / 3.0,
            resonance_trend,
            coh_zone / 2.0,
            side,
            energy_persistence + resonance_persistence,
            max(0.0, min(body_strength, 1.0)),
            max(-1.0, min(close_position, 1.0)),
            max(-1.0, min(wick_bias, 1.0)),
            max(-1.0, min(return_intensity, 1.0)),
            max(-1.0, min((body_strength_gradient * 0.5) + (close_position_gradient * 0.5), 1.0)),
        ]

    # --------------------------------------------------
    # BUFFER ITEM
    # --------------------------------------------------
    def _buffer_item(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "energy": self._safe_float(state.get("energy", 0.0)),
            "coherence": self._safe_float(state.get("coherence", 0.0)),
            "asymmetry": int(self._safe_float(state.get("asymmetry", 0.0))),
            "resonance": self._safe_float(state.get("resonance", 0.0)),
            "coh_zone": self._safe_float(state.get("coh_zone", 0.0)),
            "body_strength": self._safe_float(state.get("body_strength", 0.0)),
            "wick_bias": self._safe_float(state.get("wick_bias", 0.0)),
            "close_position": self._safe_float(state.get("close_position", 0.0)),
            "return_intensity": self._safe_float(state.get("return_intensity", 0.0)),
            "side": str(state.get("side", "NONE")),
            "timestamp": state.get("timestamp"),
        }

    # --------------------------------------------------
    # FIND BEST NODE
    # --------------------------------------------------
    def _find_best_node(self, vector: List[float]) -> Optional[MetaRegimeNode]:

        if not self.regime_nodes:
            return None

        best_node = None
        best_dist = None

        for node in self.regime_nodes:
            dist = node.distance(vector, self.vector_weights)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_node = node

        if best_node is None or best_dist is None:
            return None

        if best_dist <= self.node_match_threshold:
            return best_node

        return None

    # --------------------------------------------------
    # CREATE NODE
    # --------------------------------------------------
    def _create_node(self, vector: List[float], timestamp=None) -> MetaRegimeNode:

        node = MetaRegimeNode(
            node_id=self.next_node_id,
            center=list(vector),
            spread=[0.08] * len(vector),
            visits=1,
            meta={
                "activation": 1.0,
                "stability": 0.2,
                "quality": 0.0,
                "novelty": 1.0,
                "last_seen_ts": timestamp,
                "first_seen_ts": timestamp,
                "merge_count": 0,
                "match_count": 0,
                "miss_count": 0,
            },
        )

        self.next_node_id += 1
        self.regime_nodes.append(node)
        self._node_map[int(node.node_id)] = node
        return node

    # --------------------------------------------------
    # ADD TRANSITION
    # --------------------------------------------------
    def _add_transition(self, from_node_id: int, to_node_id: int):

        if from_node_id is None or to_node_id is None:
            return

        from_key = str(from_node_id)
        to_key = str(to_node_id)

        self.transition_graph.setdefault(from_key, {})
        self.transition_graph[from_key].setdefault(
            to_key,
            {
                "count": 0,
                "tp": 0,
                "sl": 0,
                "cancel": 0,
                "no_fill": 0,
                "market_shift": 0,
            },
        )

        self.transition_graph[from_key][to_key]["count"] += 1
        self.meta_index["total_transitions"] = int(self.meta_index.get("total_transitions", 0) or 0) + 1

    # --------------------------------------------------
    # DERIVE ATTRACTOR
    # --------------------------------------------------
    def _derive_attractor(self, node: Optional[MetaRegimeNode]) -> str:

        if node is None:
            return "neutral"

        quality = float(node.meta.get("quality", 0.0) or 0.0)
        stability = float(node.meta.get("stability", 0.0) or 0.0)
        activation = float(node.meta.get("activation", 1.0) or 1.0)

        if quality <= -0.35:
            return "defense"

        if stability < 0.35:
            return "analysis"

        if activation > 1.4 and quality >= 0.1:
            return "explore"

        if quality >= 0.0:
            return "cooperate"

        return "analysis"

    # --------------------------------------------------
    # RECORD STATE
    # --------------------------------------------------
    def record_state(self, state: Dict[str, Any]) -> Dict[str, Any]:

        timestamp = state.get("timestamp")
        vector = self._state_vector(state)
        side_key = str(state.get("side", "NONE")).upper().strip()

        self.sensory_buffer.append(self._buffer_item(state))
        if len(self.sensory_buffer) > self.max_buffer:
            self.sensory_buffer = self.sensory_buffer[-self.max_buffer:]

        self._invalidate_side_cache()

        node = self._find_best_node(vector)

        if node is None:
            node = self._create_node(vector, timestamp=timestamp)
        else:
            node.adapt(vector, timestamp=timestamp, lr=0.08)

        self._add_transition(self.last_node_id, node.node_id)
        self.last_node_id = node.node_id

        if side_key in ("LONG", "SHORT"):
            self._side_match_cache[side_key] = node

        total_states = int(self.meta_index.get("total_states", 0) or 0) + 1

        if len(self.regime_nodes) > self.max_nodes_before_consolidation:
            if (total_states - int(self._last_consolidate_state_count or 0)) >= self.consolidate_interval_states:
                self.consolidate_nodes()
                self._last_consolidate_state_count = total_states

        attractor_name = self._derive_attractor(node)
        self.attractor_state = {
            "name": attractor_name,
            "node_id": node.node_id,
        }

        self.meta_index["total_states"] = int(self.meta_index.get("total_states", 0) or 0) + 1

        self._save_counter += 1
        if self._save_counter >= self._save_interval:
            self._save()
            self._save_counter = 0

        return {
            "node_id": node.node_id,
            "attractor": attractor_name,
            "center": list(node.center),
            "quality": float(node.meta.get("quality", 0.0) or 0.0),
            "stability": float(node.meta.get("stability", 0.0) or 0.0),
        }

    # --------------------------------------------------
    # START EPISODE
    # --------------------------------------------------
    def start_episode(self, state: Dict[str, Any]):

        node_info = self.record_state(state)

        self.active_episode = {
            "start_ts": state.get("timestamp"),
            "start_node_id": node_info.get("node_id"),
            "side": str(state.get("side", "NONE")).upper().strip(),
            "states": [dict(state)],
            "path": [node_info.get("node_id")],
        }

    # --------------------------------------------------
    # STEP EPISODE
    # --------------------------------------------------
    def step_episode(self, state: Dict[str, Any]):

        if self.active_episode is None:
            self.start_episode(state)
            return

        node_info = self.record_state(state)
        node_id = node_info.get("node_id")

        self.active_episode["end_node_id"] = node_id
        self.active_episode["end_ts"] = state.get("timestamp")
        self.active_episode["states"].append(dict(state))

        path = self.active_episode.setdefault("path", [])
        if not path or path[-1] != node_id:
            path.append(node_id)

    # --------------------------------------------------
    # FINALIZE EPISODE
    # --------------------------------------------------
    def finalize_episode(self, outcome: str, rr: float = 0.0, save: bool = True):

        if self.active_episode is None:
            return

        episode = dict(self.active_episode)
        episode["outcome"] = str(outcome)
        episode["rr"] = float(rr or 0.0)
        episode["length"] = len(episode.get("states", []))

        self.episodes.append(episode)
        if len(self.episodes) > self.max_episodes:
            self.episodes = self.episodes[-self.max_episodes:]

        self.meta_index["total_episodes"] = int(self.meta_index.get("total_episodes", 0) or 0) + 1
        self.meta_index["last_outcome"] = str(outcome)

        self.active_episode = None

        if save:
            self._save()

    # --------------------------------------------------
    # MATCH CURRENT NODE
    # --------------------------------------------------
    def _match_current_node(self, side: str = None) -> Optional[MetaRegimeNode]:

        if not self.sensory_buffer:
            return None

        last = self.sensory_buffer[-1]

        state = {
            "energy": last.get("energy", 0.0),
            "coherence": last.get("coherence", 0.0),
            "asymmetry": last.get("asymmetry", 0.0),
            "resonance": last.get("resonance", 0.0),
            "coh_zone": last.get("coh_zone", 0.0),
            "body_strength": last.get("body_strength", 0.0),
            "wick_bias": last.get("wick_bias", 0.0),
            "close_position": last.get("close_position", 0.0),
            "return_intensity": last.get("return_intensity", 0.0),
            "side": side,
            "timestamp": last.get("timestamp"),
        }

        vector = self._state_vector(state)
        return self._find_best_node(vector)

    # --------------------------------------------------
    # SIDE NODE
    # --------------------------------------------------
    def _side_node(self, side: str) -> Optional[MetaRegimeNode]:

        side_key = str(side).upper().strip()
        if side_key not in ("LONG", "SHORT"):
            return None

        if side_key in self._side_match_cache:
            return self._side_match_cache.get(side_key)

        node = self._match_current_node(side_key)
        self._side_match_cache[side_key] = node
        return node

    # --------------------------------------------------
    # RESOLVE REGIME NODE
    # --------------------------------------------------
    def _resolve_regime_node(self, side: str, state: Optional[Dict[str, Any]] = None, node_id=None) -> Optional[MetaRegimeNode]:

        side_key = str(side).upper().strip()

        if side_key not in ("LONG", "SHORT"):
            return None

        if node_id is not None:
            node = self._get_node_by_id(node_id)
            if node is not None:
                return node

        if isinstance(state, dict):
            state_copy = dict(state)
            state_copy["side"] = side_key
            vector = self._state_vector(state_copy)
            node = self._find_best_node(vector)
            if node is not None:
                return node

        return self._side_node(side_key)

    # --------------------------------------------------
    # REGIME RR
    # --------------------------------------------------
    def regime_rr(self, energy_value, side, state: Optional[Dict[str, Any]] = None, node_id=None):

        default_rr = float(getattr(Config, "RR", 2.0) or 2.0)
        min_rr = float(getattr(Config, "MIN_RR", 2.0) or 2.0)
        max_rr = float(getattr(Config, "MAX_RR", 4.0) or 4.0)

        node = self._resolve_regime_node(side, state=state, node_id=node_id)
        if node is None:
            return default_rr

        stats = node.side_stats.get(str(side).upper().strip(), {})
        rr_sum = float(stats.get("rr_sum", 0.0) or 0.0)
        rr_count = int(stats.get("rr_count", 0) or 0)

        if rr_count <= 0:
            return default_rr

        avg_rr = rr_sum / rr_count
        quality = float(node.meta.get("quality", 0.0) or 0.0)
        stability = float(node.meta.get("stability", 0.0) or 0.0)

        rr_target = avg_rr
        rr_target += quality * 0.35
        rr_target += (stability - 0.5) * 0.25

        rr_target = max(min_rr, min(rr_target, max_rr))
        return float(rr_target)

    # --------------------------------------------------
    # REGIME ENTRY OFFSET
    # --------------------------------------------------
    def regime_entry_offset(self, energy_value, side, state: Optional[Dict[str, Any]] = None, node_id=None):

        node = self._resolve_regime_node(side, state=state, node_id=node_id)
        if node is None:
            return 0.0

        stats = node.side_stats.get(str(side).upper().strip(), {})
        count = int(stats.get("entry_shift_count", 0) or 0)
        total = float(stats.get("entry_shift_sum", 0.0) or 0.0)

        if count <= 0:
            return 0.0

        stability = float(node.meta.get("stability", 0.0) or 0.0)
        avg_shift = total / count

        return max(0.0, float(avg_shift * (0.75 + stability * 0.5)))

    # --------------------------------------------------
    # REGIME ENTRY DISTANCE
    # --------------------------------------------------
    def regime_entry_distance(self, energy_value, side, state: Optional[Dict[str, Any]] = None, node_id=None):

        node = self._resolve_regime_node(side, state=state, node_id=node_id)
        if node is None:
            return 0.0

        stats = node.side_stats.get(str(side).upper().strip(), {})
        count = int(stats.get("entry_distance_count", 0) or 0)
        total = float(stats.get("entry_distance_sum", 0.0) or 0.0)

        if count <= 0:
            return 0.0

        value = total / count
        return max(0.0, float(value))

    # --------------------------------------------------
    # REGIME EFFICIENCY
    # --------------------------------------------------
    def regime_efficiency(self, energy_value, side, state: Optional[Dict[str, Any]] = None, node_id=None):

        node = self._resolve_regime_node(side, state=state, node_id=node_id)
        if node is None:
            return 0.5

        stats = node.side_stats.get(str(side).upper().strip(), {})

        tp = int(stats.get("tp", 0) or 0)
        sl = int(stats.get("sl", 0) or 0)
        cancel = int(stats.get("cancel", 0) or 0)
        no_fill = int(stats.get("no_fill", 0) or 0)
        market_shift = int(stats.get("market_shift", 0) or 0)

        total = tp + sl + cancel + no_fill + market_shift
        if total <= 0:
            return 0.5

        efficiency = 0.0
        efficiency += (tp / total) * 1.0
        efficiency -= (sl / total) * 0.75
        efficiency -= ((cancel + no_fill + market_shift) / total) * 0.40
        efficiency += float(node.meta.get("quality", 0.0) or 0.0) * 0.20

        return float(max(0.0, min(1.0, 0.5 + efficiency * 0.5)))

    # --------------------------------------------------
    # UPDATE REWARD
    # --------------------------------------------------
    def update_reward(
        self,
        energy_value,
        outcome,
        side,
        rr,
        entry_shift=0.0,
        entry_quality=0.0,
        node_id=None,
        entry_distance=0.0,
        risk=0.0,
        reward=0.0,
        hold_bars=0,
    ):

        side_key = str(side).upper().strip()
        if side_key not in ("LONG", "SHORT"):
            return

        node = None

        if node_id is not None:
            node = self._get_node_by_id(node_id)

        if node is None:
            node = self._side_node(side_key)

        if node is None:
            base_state = {
                "energy": energy_value,
                "coherence": 0.0,
                "asymmetry": 0.0,
                "resonance": 0.0,
                "coh_zone": 0.0,
                "body_strength": 0.0,
                "wick_bias": 0.0,
                "close_position": 0.0,
                "return_intensity": 0.0,
                "side": side_key,
                "timestamp": None,
            }
            node = self._create_node(self._state_vector(base_state), timestamp=None)

        stats = node.side_stats[side_key]

        stats["entry_shift_sum"] += abs(float(entry_shift or 0.0))
        stats["entry_shift_count"] += 1

        stats["entry_quality_sum"] += float(entry_quality or 0.0)
        stats["entry_quality_count"] += 1

        stats["entry_distance_sum"] += abs(float(entry_distance or 0.0))
        stats["entry_distance_count"] += 1

        stats["risk_sum"] += abs(float(risk or 0.0))
        stats["risk_count"] += 1

        stats["reward_sum"] += abs(float(reward or 0.0))
        stats["reward_count"] += 1

        stats["hold_bars_sum"] += max(0.0, float(hold_bars or 0.0))
        stats["hold_bars_count"] += 1

        score_delta = 0.0
        outcome_key = str(outcome).lower().strip()

        if outcome_key == "tp":
            stats["tp"] += 1
            stats["rr_sum"] += float(rr or 0.0)
            stats["rr_count"] += 1
            score_delta = 1.0 + float(rr or 0.0) * 0.25

        elif outcome_key == "sl":
            stats["sl"] += 1
            stats["rr_sum"] -= abs(float(rr or 0.0))
            stats["rr_count"] += 1
            score_delta = -1.0 - abs(float(rr or 0.0)) * 0.25

        elif outcome_key == "cancel":
            stats["cancel"] += 1
            score_delta = -0.35

        elif outcome_key == "no_fill":
            stats["no_fill"] += 1
            score_delta = -0.20

        elif outcome_key == "market_shift":
            stats["market_shift"] += 1
            score_delta = -0.50

        stats["score_sum"] += float(score_delta)
        stats["score_count"] += 1

        node.meta["activation"] = max(0.25, min(3.0, float(node.meta.get("activation", 1.0) or 1.0) + (score_delta * 0.04)))
        node._refresh_meta_quality()

        self.reward_traces.append({
            "node_id": node.node_id,
            "energy": float(energy_value or 0.0),
            "outcome": outcome_key,
            "side": side_key,
            "rr": float(rr or 0.0),
            "entry_shift": float(entry_shift or 0.0),
            "entry_quality": float(entry_quality or 0.0),
            "entry_distance": float(entry_distance or 0.0),
            "risk": abs(float(risk or 0.0)),
            "reward": abs(float(reward or 0.0)),
            "hold_bars": max(0.0, float(hold_bars or 0.0)),
        })

        if len(self.reward_traces) > self.max_reward_traces:
            self.reward_traces = self.reward_traces[-self.max_reward_traces:]

        if self.last_node_id is not None:
            from_key = str(self.last_node_id)
            to_key = str(node.node_id)

            if from_key in self.transition_graph and to_key in self.transition_graph[from_key]:
                bucket = self.transition_graph[from_key][to_key]
                bucket[outcome_key] = int(bucket.get(outcome_key, 0) or 0) + 1

        self.finalize_episode(outcome=outcome_key, rr=float(rr or 0.0), save=False)
        self._invalidate_side_cache()
        self._save()

    # --------------------------------------------------
    # STRONGEST
    # --------------------------------------------------
    def strongest(self):

        if not self.regime_nodes:
            return None

        best_node = None
        best_score = None

        for node in self.regime_nodes:
            score = 0.0
            score += float(node.visits)
            score += float(node.meta.get("quality", 0.0) or 0.0) * 20.0
            score += float(node.meta.get("stability", 0.0) or 0.0) * 10.0

            if best_score is None or score > best_score:
                best_score = score
                best_node = node

        if best_node is None:
            return None

        return {
            "node_id": best_node.node_id,
            "center": float(best_node.center[0]) if best_node.center else 0.0,
            "visits": int(best_node.visits),
            "quality": float(best_node.meta.get("quality", 0.0) or 0.0),
            "stability": float(best_node.meta.get("stability", 0.0) or 0.0),
        }

    # --------------------------------------------------
    # REPLAY IMPULSE
    # --------------------------------------------------
    def replay_impulse(self, replay_scale=0.25):

        if not self.reward_traces:
            return 0.0

        positives = [
            item for item in self.reward_traces
            if str(item.get("outcome", "")).lower().strip() == "tp"
        ]

        if not positives:
            return 0.0

        item = random.choice(positives)
        return float(float(item.get("energy", 0.0) or 0.0) * float(replay_scale or 0.25))

    # --------------------------------------------------
    # PREDICT NEXT REGIME
    # --------------------------------------------------
    def predict_next_regime(self):

        if self.last_node_id is None:
            return None

        from_key = str(self.last_node_id)
        transitions = self.transition_graph.get(from_key)

        if not transitions:
            return None

        total = 0
        for data in transitions.values():
            total += int(data.get("count", 0) or 0)

        if total <= 0:
            return None

        best_node = None
        best_probability = 0.0
        best_quality = None

        for node_id, data in transitions.items():
            probability = float(int(data.get("count", 0) or 0)) / float(total)
            quality = (
                float(int(data.get("tp", 0) or 0))
                - float(int(data.get("sl", 0) or 0))
                - 0.5 * (
                    float(int(data.get("cancel", 0) or 0))
                    + float(int(data.get("no_fill", 0) or 0))
                    + float(int(data.get("market_shift", 0) or 0))
                )
            )

            choose = False

            if probability > best_probability:
                choose = True
            elif probability == best_probability and (best_quality is None or quality > best_quality):
                choose = True

            if choose:
                best_node = int(node_id)
                best_probability = probability
                best_quality = quality

        return {
            "next_node": best_node,
            "probability": float(best_probability),
            "transition_quality": float(best_quality or 0.0),
        }

    # --------------------------------------------------
    # CONSOLIDATE NODES
    # --------------------------------------------------
    def consolidate_nodes(self, merge_distance: float = 2.8, min_visits: int = 3):

        if len(self.regime_nodes) < 2:
            return

        merged: List[MetaRegimeNode] = []

        for node in self.regime_nodes:
            absorbed = False

            for target in merged:
                dist = target.distance(node.center, self.vector_weights)

                if dist <= merge_distance:
                    total_visits = target.visits + node.visits
                    if total_visits <= 0:
                        continue

                    for i in range(min(len(target.center), len(node.center))):
                        target.center[i] = (
                            (target.center[i] * target.visits)
                            + (node.center[i] * node.visits)
                        ) / total_visits

                        target.spread[i] = max(
                            0.02,
                            min(
                                (
                                    (target.spread[i] * target.visits)
                                    + (node.spread[i] * node.visits)
                                ) / total_visits,
                                3.0,
                            ),
                        )

                    target.visits = total_visits
                    target.meta["merge_count"] = int(target.meta.get("merge_count", 0) or 0) + 1

                    for side_key in ("LONG", "SHORT"):
                        for key, value in node.side_stats[side_key].items():
                            current = target.side_stats[side_key].get(key)
                            if isinstance(value, (int, float)) and isinstance(current, (int, float)):
                                target.side_stats[side_key][key] = current + value

                    target._refresh_meta_quality()
                    absorbed = True
                    break

            if not absorbed:
                merged.append(node)

        self.regime_nodes = [node for node in merged if int(node.visits) >= int(min_visits)]
        self._rebuild_node_map()
        self._invalidate_side_cache()
        self._save()


# ==================================================
# BACKWARDS-COMPAT ALIAS
# ==================================================
class MCMMemoryEngine(MCMMetaVectorMemory):
    pass
