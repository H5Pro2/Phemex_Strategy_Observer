# ==================================================
# memory_state.py
# Persistente Erfahrungsspeicherung
# - Signature Memory
# - Context Cluster
# - MCM Memory
# ==================================================
import json
import os
from config import Config


# --------------------------------------------------
# PATH
# --------------------------------------------------
def _memory_state_path(path: str | None = None) -> str:

    if path is not None:
        return str(path)

    configured = getattr(Config, "MCM_MEMORY_STATE_PATH", "bot_memory/memory_state.json")
    configured = str(configured or "bot_memory/memory_state.json")
    return configured


# --------------------------------------------------
# FS
# --------------------------------------------------
def _ensure_dir(path: str):

    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


# --------------------------------------------------
# CAST HELPERS
# --------------------------------------------------
def _to_int(value, default: int = 0) -> int:

    try:
        return int(value)
    except Exception:
        return int(default)

# --------------------------------------------------
def normalize_json_state(value):

    if isinstance(value, dict):
        normalized = {}

        for key, item in value.items():
            if key is None:
                continue

            normalized[str(key)] = normalize_json_state(item)

        return normalized

    if isinstance(value, list):
        return [normalize_json_state(item) for item in list(value or [])[:128]]

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return _to_str(value, None)

# --------------------------------------------------
def _to_float(value, default: float = 0.0) -> float:

    try:
        return float(value)
    except Exception:
        return float(default)


# --------------------------------------------------
def _to_str(value, default: str | None = None) -> str | None:

    if value is None:
        return default

    try:
        return str(value)
    except Exception:
        return default


# --------------------------------------------------
def _to_float_list(values) -> list[float]:

    cleaned = []

    for value in list(values or []):
        try:
            cleaned.append(float(value))
        except Exception:
            continue

    return cleaned


# --------------------------------------------------
def _to_str_list(values) -> list[str]:

    cleaned = []

    for value in list(values or []):
        if value is None:
            continue

        try:
            cleaned.append(str(value))
        except Exception:
            continue

    return cleaned


# --------------------------------------------------
# NORMALIZE SIGNATURE MEMORY
# --------------------------------------------------
def normalize_signature_memory(signature_memory) -> dict:

    normalized = {}

    if not isinstance(signature_memory, dict):
        return normalized

    for key, item in signature_memory.items():
        if key is None or not isinstance(item, dict):
            continue

        signature_key = str(key).strip()
        if not signature_key:
            continue

        normalized[signature_key] = {
            "seen": max(0, _to_int(item.get("seen", 0), 0)),
            "tp": max(0, _to_int(item.get("tp", 0), 0)),
            "sl": max(0, _to_int(item.get("sl", 0), 0)),
            "cancel": max(0, _to_int(item.get("cancel", 0), 0)),
            "timeout": max(0, _to_int(item.get("timeout", 0), 0)),
            "score": max(-6.0, min(6.0, _to_float(item.get("score", 0.0), 0.0))),
            "last_outcome": _to_str(item.get("last_outcome"), None),
            "age": max(0, _to_int(item.get("age", 0), 0)),
            "signature_vector": _to_float_list(item.get("signature_vector", [])),
        }

    if len(normalized) > 180:
        sorted_items = sorted(
            normalized.items(),
            key=lambda entry: (
                abs(_to_float((entry[1] or {}).get("score", 0.0), 0.0)),
                -max(0, _to_int((entry[1] or {}).get("age", 0), 0)),
                max(0, _to_int((entry[1] or {}).get("seen", 0), 0)),
            ),
            reverse=True,
        )[:180]
        normalized = dict(sorted_items)

    return normalized


# --------------------------------------------------
# NORMALIZE CONTEXT CLUSTERS
# --------------------------------------------------
def normalize_context_clusters(context_clusters) -> dict:

    normalized = {}

    if not isinstance(context_clusters, dict):
        return normalized

    for cluster_id, item in context_clusters.items():
        if cluster_id is None or not isinstance(item, dict):
            continue

        cluster_key = str(cluster_id).strip()
        if not cluster_key:
            continue

        normalized[cluster_key] = {
            "cluster_id": _to_str(item.get("cluster_id"), cluster_key),
            "center_vector": _to_float_list(item.get("center_vector", [])),
            "variance": max(0.0, _to_float(item.get("variance", 0.0), 0.0)),
            "radius": max(0.0, _to_float(item.get("radius", 0.0), 0.0)),
            "seen": max(0, _to_int(item.get("seen", 0), 0)),
            "tp": max(0, _to_int(item.get("tp", 0), 0)),
            "sl": max(0, _to_int(item.get("sl", 0), 0)),
            "cancel": max(0, _to_int(item.get("cancel", 0), 0)),
            "timeout": max(0, _to_int(item.get("timeout", 0), 0)),
            "score": max(-12.0, min(12.0, _to_float(item.get("score", 0.0), 0.0))),
            "trust": max(0.0, min(1.0, _to_float(item.get("trust", 0.0), 0.0))),
            "age": max(0, _to_int(item.get("age", 0), 0)),
            "signature_keys": _to_str_list(item.get("signature_keys", []))[-24:],
            "last_signature_key": _to_str(item.get("last_signature_key"), None),
            "last_outcome": _to_str(item.get("last_outcome"), None),
            "last_distance": max(0.0, _to_float(item.get("last_distance", 0.0), 0.0)),
        }

    return normalized


# --------------------------------------------------
# NORMALIZE MCM MEMORY
# --------------------------------------------------
def normalize_mcm_memory(memory_items) -> list[dict]:

    normalized = []

    for item in list(memory_items or []):
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "center": _to_float(item.get("center", 0.0), 0.0),
                "strength": max(1, _to_int(item.get("strength", 1), 1)),
            }
        )

    normalized = sorted(
        normalized,
        key=lambda item: max(1, _to_int(item.get("strength", 1), 1)),
        reverse=True,
    )[:24]

    return normalized


# --------------------------------------------------
# BUILD STATE
# --------------------------------------------------
def build_memory_state(bot, include_runtime_state: bool = True) -> dict:

    if bot is None:
        return {
            "signature_memory": {},
            "context_clusters": {},
            "context_cluster_seq": 0,
            "last_signature_key": None,
            "last_signature_outcome": None,
            "last_signature_context": None,
            "last_context_cluster_id": None,
            "last_context_cluster_key": None,
            "mcm_runtime_snapshot": {},
            "mcm_runtime_decision_state": {},
            "mcm_runtime_brain_snapshot": {},
            "mcm_runtime_market_ticks": 0,
            "mcm_decision_episode": {},
            "mcm_experience_space": {},
            "mcm_last_observe_timestamp": None,
            "mcm_memory": [],
            "mcm_last_attractor": None,
            "mcm_last_action": None,
        }

    mcm_memory = []
    mcm_brain = getattr(bot, "mcm_brain", None)

    if isinstance(mcm_brain, dict):
        memory_obj = mcm_brain.get("memory")
        memory_items = getattr(memory_obj, "memory", None)
        mcm_memory = normalize_mcm_memory(memory_items)

    payload = {
        "signature_memory": normalize_signature_memory(getattr(bot, "signature_memory", {})),
        "context_clusters": normalize_context_clusters(getattr(bot, "context_clusters", {})),
        "context_cluster_seq": max(0, _to_int(getattr(bot, "context_cluster_seq", 0), 0)),
        "last_signature_key": _to_str(getattr(bot, "last_signature_key", None), None),
        "last_signature_outcome": _to_str(getattr(bot, "last_signature_outcome", None), None),
        "last_signature_context": normalize_json_state(getattr(bot, "last_signature_context", None)),
        "last_context_cluster_id": _to_str(getattr(bot, "last_context_cluster_id", None), None),
        "last_context_cluster_key": _to_str(getattr(bot, "last_context_cluster_key", None), None),
        "focus_point": _to_float(getattr(bot, "focus_point", 0.0), 0.0),
        "focus_confidence": _to_float(getattr(bot, "focus_confidence", 0.0), 0.0),
        "target_lock": _to_float(getattr(bot, "target_lock", 0.0), 0.0),
        "target_drift": _to_float(getattr(bot, "target_drift", 0.0), 0.0),
        "entry_expectation": _to_float(getattr(bot, "entry_expectation", 0.0), 0.0),
        "target_expectation": _to_float(getattr(bot, "target_expectation", 0.0), 0.0),
        "approach_pressure": _to_float(getattr(bot, "approach_pressure", 0.0), 0.0),
        "pressure_release": _to_float(getattr(bot, "pressure_release", 0.0), 0.0),
        "experience_regulation": _to_float(getattr(bot, "experience_regulation", 0.0), 0.0),
        "reflection_maturity": _to_float(getattr(bot, "reflection_maturity", 0.0), 0.0),
        "load_bearing_capacity": _to_float(getattr(bot, "load_bearing_capacity", 0.0), 0.0),
        "protective_width_regulation": _to_float(getattr(bot, "protective_width_regulation", 0.0), 0.0),
        "protective_courage": _to_float(getattr(bot, "protective_courage", 0.0), 0.0),
        "inhibition_level": _to_float(getattr(bot, "inhibition_level", 0.0), 0.0),
        "habituation_level": _to_float(getattr(bot, "habituation_level", 0.0), 0.0),
        "competition_bias": _to_float(getattr(bot, "competition_bias", 0.0), 0.0),
        "observation_mode": bool(getattr(bot, "observation_mode", False)),
        "last_signal_relevance": _to_float(getattr(bot, "last_signal_relevance", 0.0), 0.0),
        "structure_perception_state": normalize_json_state(getattr(bot, "structure_perception_state", {})),
        "perception_state": normalize_json_state(getattr(bot, "perception_state", {})),
        "outer_visual_perception_state": normalize_json_state(getattr(bot, "outer_visual_perception_state", {})),
        "inner_field_perception_state": normalize_json_state(getattr(bot, "inner_field_perception_state", {})),
        "processing_state": normalize_json_state(getattr(bot, "processing_state", {})),
        "expectation_state": normalize_json_state(getattr(bot, "expectation_state", {})),
        "felt_state": normalize_json_state(getattr(bot, "felt_state", {})),
        "thought_state": normalize_json_state(getattr(bot, "thought_state", {})),
        "meta_regulation_state": normalize_json_state(getattr(bot, "meta_regulation_state", {})),
        "last_outcome_decomposition": normalize_json_state(getattr(bot, "last_outcome_decomposition", {})),
        "mcm_memory": mcm_memory,
        "mcm_last_attractor": _to_str(getattr(bot, "mcm_last_attractor", None), None),
        "mcm_last_action": _to_str(getattr(bot, "mcm_last_action", None), None),
        "field_density": _to_float(getattr(bot, "field_density", 0.0), 0.0),
        "field_stability": _to_float(getattr(bot, "field_stability", 0.0), 0.0),
        "regulatory_load": _to_float(getattr(bot, "regulatory_load", 0.0), 0.0),
        "action_capacity": _to_float(getattr(bot, "action_capacity", 0.0), 0.0),
        "recovery_need": _to_float(getattr(bot, "recovery_need", 0.0), 0.0),
        "survival_pressure": _to_float(getattr(bot, "survival_pressure", 0.0), 0.0),
    }

    if bool(include_runtime_state):
        payload.update({
            "mcm_runtime_snapshot": normalize_json_state(getattr(bot, "mcm_runtime_snapshot", {})),
            "mcm_runtime_decision_state": normalize_json_state(getattr(bot, "mcm_runtime_decision_state", {})),
            "mcm_runtime_brain_snapshot": normalize_json_state(getattr(bot, "mcm_runtime_brain_snapshot", {})),
            "mcm_runtime_market_ticks": max(0, _to_int(getattr(bot, "mcm_runtime_market_ticks", 0), 0)),
            "mcm_decision_episode": normalize_json_state(getattr(bot, "mcm_decision_episode", {})),
            "mcm_decision_episode_internal": normalize_json_state(getattr(bot, "mcm_decision_episode_internal", {})),
            "mcm_experience_space": normalize_json_state(getattr(bot, "mcm_experience_space", {})),
            "mcm_last_observe_timestamp": getattr(bot, "mcm_last_observe_timestamp", None),
        })

    return payload


# --------------------------------------------------
# APPLY STATE
# --------------------------------------------------
def apply_memory_state(bot, state: dict | None) -> dict:

    payload = dict(state or {})

    if bot is None:
        return payload

    bot.signature_memory = normalize_signature_memory(payload.get("signature_memory", {}))
    bot.context_clusters = normalize_context_clusters(payload.get("context_clusters", {}))
    bot.context_cluster_seq = max(0, _to_int(payload.get("context_cluster_seq", 0), 0))

    bot.last_signature_key = _to_str(payload.get("last_signature_key"), None)
    bot.last_signature_outcome = _to_str(payload.get("last_signature_outcome"), None)
    bot.last_signature_context = normalize_json_state(payload.get("last_signature_context"))
    bot.last_context_cluster_id = _to_str(payload.get("last_context_cluster_id"), None)
    bot.last_context_cluster_key = _to_str(payload.get("last_context_cluster_key"), None)
    bot.focus_point = _to_float(payload.get("focus_point", 0.0), 0.0)
    bot.focus_confidence = _to_float(payload.get("focus_confidence", 0.0), 0.0)
    bot.target_lock = _to_float(payload.get("target_lock", 0.0), 0.0)
    bot.target_drift = _to_float(payload.get("target_drift", 0.0), 0.0)
    bot.entry_expectation = _to_float(payload.get("entry_expectation", 0.0), 0.0)
    bot.target_expectation = _to_float(payload.get("target_expectation", 0.0), 0.0)
    bot.approach_pressure = _to_float(payload.get("approach_pressure", 0.0), 0.0)
    bot.pressure_release = _to_float(payload.get("pressure_release", 0.0), 0.0)
    bot.experience_regulation = _to_float(payload.get("experience_regulation", 0.0), 0.0)
    bot.reflection_maturity = _to_float(payload.get("reflection_maturity", 0.0), 0.0)
    bot.load_bearing_capacity = _to_float(payload.get("load_bearing_capacity", 0.0), 0.0)
    bot.protective_width_regulation = _to_float(payload.get("protective_width_regulation", 0.0), 0.0)
    bot.protective_courage = _to_float(payload.get("protective_courage", 0.0), 0.0)
    bot.inhibition_level = _to_float(payload.get("inhibition_level", 0.0), 0.0)
    bot.habituation_level = _to_float(payload.get("habituation_level", 0.0), 0.0)
    bot.competition_bias = _to_float(payload.get("competition_bias", 0.0), 0.0)
    bot.observation_mode = bool(payload.get("observation_mode", False))
    bot.last_signal_relevance = _to_float(payload.get("last_signal_relevance", 0.0), 0.0)
    bot.structure_perception_state = normalize_json_state(payload.get("structure_perception_state", {}))
    bot.perception_state = normalize_json_state(payload.get("perception_state", {}))
    bot.outer_visual_perception_state = normalize_json_state(payload.get("outer_visual_perception_state", {}))
    bot.inner_field_perception_state = normalize_json_state(payload.get("inner_field_perception_state", {}))
    bot.processing_state = normalize_json_state(payload.get("processing_state", {}))
    bot.expectation_state = normalize_json_state(payload.get("expectation_state", {}))
    bot.felt_state = normalize_json_state(payload.get("felt_state", {}))
    bot.thought_state = normalize_json_state(payload.get("thought_state", {}))
    bot.meta_regulation_state = normalize_json_state(payload.get("meta_regulation_state", {}))
    bot.last_outcome_decomposition = normalize_json_state(payload.get("last_outcome_decomposition", {}))
    bot.mcm_runtime_snapshot = normalize_json_state(payload.get("mcm_runtime_snapshot", {}))
    bot.mcm_runtime_decision_state = normalize_json_state(payload.get("mcm_runtime_decision_state", {}))
    bot.mcm_runtime_brain_snapshot = normalize_json_state(payload.get("mcm_runtime_brain_snapshot", {}))
    bot.mcm_runtime_market_ticks = max(0, _to_int(payload.get("mcm_runtime_market_ticks", 0), 0))
    bot.mcm_decision_episode = normalize_json_state(payload.get("mcm_decision_episode", {}))
    bot.mcm_decision_episode_internal = normalize_json_state(payload.get("mcm_decision_episode_internal", {}))
    bot.mcm_experience_space = normalize_json_state(payload.get("mcm_experience_space", {}))
    bot.mcm_last_observe_timestamp = payload.get("mcm_last_observe_timestamp", None)
    bot.mcm_last_attractor = _to_str(payload.get("mcm_last_attractor"), None)
    bot.mcm_last_action = _to_str(payload.get("mcm_last_action"), None)
    bot.field_density = _to_float(payload.get("field_density", 0.0), 0.0)
    bot.field_stability = _to_float(payload.get("field_stability", 0.0), 0.0)
    bot.regulatory_load = _to_float(payload.get("regulatory_load", 0.0), 0.0)
    bot.action_capacity = _to_float(payload.get("action_capacity", 0.0), 0.0)
    bot.recovery_need = _to_float(payload.get("recovery_need", 0.0), 0.0)
    bot.survival_pressure = _to_float(payload.get("survival_pressure", 0.0), 0.0)

    mcm_brain = getattr(bot, "mcm_brain", None)
    if isinstance(mcm_brain, dict):
        memory_obj = mcm_brain.get("memory")
        if memory_obj is not None and hasattr(memory_obj, "memory"):
            memory_obj.memory = normalize_mcm_memory(payload.get("mcm_memory", []))

    return build_memory_state(bot)


# --------------------------------------------------
# READ
# --------------------------------------------------
def read_memory_state(path: str | None = None) -> dict:

    filepath = _memory_state_path(path)

    default_state = {
        "signature_memory": {},
        "context_clusters": {},
        "context_cluster_seq": 0,
        "last_signature_key": None,
        "last_signature_outcome": None,
        "last_signature_context": None,
        "last_context_cluster_id": None,
        "last_context_cluster_key": None,
        "focus_point": 0.0,
        "focus_confidence": 0.0,
        "target_lock": 0.0,
        "target_drift": 0.0,
        "entry_expectation": 0.0,
        "target_expectation": 0.0,
        "approach_pressure": 0.0,
        "pressure_release": 0.0,
        "experience_regulation": 0.0,
        "reflection_maturity": 0.0,
        "load_bearing_capacity": 0.0,
        "protective_width_regulation": 0.0,
        "protective_courage": 0.0,
        "inhibition_level": 0.0,
        "habituation_level": 0.0,
        "competition_bias": 0.0,
        "observation_mode": False,
        "last_signal_relevance": 0.0,
        "structure_perception_state": {},
        "perception_state": {},
        "outer_visual_perception_state": {},
        "inner_field_perception_state": {},
        "processing_state": {},
        "expectation_state": {},
        "felt_state": {},
        "thought_state": {},
        "meta_regulation_state": {},
        "last_outcome_decomposition": {},
        "mcm_runtime_snapshot": {},
        "mcm_runtime_decision_state": {},
        "mcm_runtime_brain_snapshot": {},
        "mcm_runtime_market_ticks": 0,
        "mcm_decision_episode": {},
        "mcm_decision_episode_internal": {},
        "mcm_experience_space": {},
        "mcm_last_observe_timestamp": None,
        "mcm_memory": [],
        "mcm_last_attractor": None,
        "mcm_last_action": None,
        "field_density": 0.0,
        "field_stability": 0.0,
        "regulatory_load": 0.0,
        "action_capacity": 0.0,
        "recovery_need": 0.0,
        "survival_pressure": 0.0,
    }

    if not os.path.exists(filepath):
        return dict(default_state)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return dict(default_state)

    return {
        "signature_memory": normalize_signature_memory((raw or {}).get("signature_memory", {})),
        "context_clusters": normalize_context_clusters((raw or {}).get("context_clusters", {})),
        "context_cluster_seq": max(0, _to_int((raw or {}).get("context_cluster_seq", 0), 0)),
        "last_signature_key": _to_str((raw or {}).get("last_signature_key"), None),
        "last_signature_outcome": _to_str((raw or {}).get("last_signature_outcome"), None),
        "last_signature_context": normalize_json_state((raw or {}).get("last_signature_context")),
        "last_context_cluster_id": _to_str((raw or {}).get("last_context_cluster_id"), None),
        "last_context_cluster_key": _to_str((raw or {}).get("last_context_cluster_key"), None),
        "focus_point": _to_float((raw or {}).get("focus_point", 0.0), 0.0),
        "focus_confidence": _to_float((raw or {}).get("focus_confidence", 0.0), 0.0),
        "target_lock": _to_float((raw or {}).get("target_lock", 0.0), 0.0),
        "target_drift": _to_float((raw or {}).get("target_drift", 0.0), 0.0),
        "entry_expectation": _to_float((raw or {}).get("entry_expectation", 0.0), 0.0),
        "target_expectation": _to_float((raw or {}).get("target_expectation", 0.0), 0.0),
        "approach_pressure": _to_float((raw or {}).get("approach_pressure", 0.0), 0.0),
        "pressure_release": _to_float((raw or {}).get("pressure_release", 0.0), 0.0),
        "experience_regulation": _to_float((raw or {}).get("experience_regulation", 0.0), 0.0),
        "reflection_maturity": _to_float((raw or {}).get("reflection_maturity", 0.0), 0.0),
        "load_bearing_capacity": _to_float((raw or {}).get("load_bearing_capacity", 0.0), 0.0),
        "protective_width_regulation": _to_float((raw or {}).get("protective_width_regulation", 0.0), 0.0),
        "protective_courage": _to_float((raw or {}).get("protective_courage", 0.0), 0.0),
        "inhibition_level": _to_float((raw or {}).get("inhibition_level", 0.0), 0.0),
        "habituation_level": _to_float((raw or {}).get("habituation_level", 0.0), 0.0),
        "competition_bias": _to_float((raw or {}).get("competition_bias", 0.0), 0.0),
        "observation_mode": bool((raw or {}).get("observation_mode", False)),
        "last_signal_relevance": _to_float((raw or {}).get("last_signal_relevance", 0.0), 0.0),
        "structure_perception_state": normalize_json_state((raw or {}).get("structure_perception_state", {})),
        "perception_state": normalize_json_state((raw or {}).get("perception_state", {})),
        "outer_visual_perception_state": normalize_json_state((raw or {}).get("outer_visual_perception_state", {})),
        "inner_field_perception_state": normalize_json_state((raw or {}).get("inner_field_perception_state", {})),
        "processing_state": normalize_json_state((raw or {}).get("processing_state", {})),
        "expectation_state": normalize_json_state((raw or {}).get("expectation_state", {})),
        "felt_state": normalize_json_state((raw or {}).get("felt_state", {})),
        "thought_state": normalize_json_state((raw or {}).get("thought_state", {})),
        "meta_regulation_state": normalize_json_state((raw or {}).get("meta_regulation_state", {})),
        "last_outcome_decomposition": normalize_json_state((raw or {}).get("last_outcome_decomposition", {})),
        "mcm_runtime_snapshot": normalize_json_state((raw or {}).get("mcm_runtime_snapshot", {})),
        "mcm_runtime_decision_state": normalize_json_state((raw or {}).get("mcm_runtime_decision_state", {})),
        "mcm_runtime_brain_snapshot": normalize_json_state((raw or {}).get("mcm_runtime_brain_snapshot", {})),
        "mcm_runtime_market_ticks": max(0, _to_int((raw or {}).get("mcm_runtime_market_ticks", 0), 0)),
        "mcm_decision_episode": normalize_json_state((raw or {}).get("mcm_decision_episode", {})),
        "mcm_decision_episode_internal": normalize_json_state((raw or {}).get("mcm_decision_episode_internal", {})),
        "mcm_experience_space": normalize_json_state((raw or {}).get("mcm_experience_space", {})),
        "mcm_last_observe_timestamp": (raw or {}).get("mcm_last_observe_timestamp", None),
        "mcm_memory": normalize_mcm_memory((raw or {}).get("mcm_memory", [])),
        "mcm_last_attractor": _to_str((raw or {}).get("mcm_last_attractor"), None),
        "mcm_last_action": _to_str((raw or {}).get("mcm_last_action"), None),
        "field_density": _to_float((raw or {}).get("field_density", 0.0), 0.0),
        "field_stability": _to_float((raw or {}).get("field_stability", 0.0), 0.0),
        "regulatory_load": _to_float((raw or {}).get("regulatory_load", 0.0), 0.0),
        "action_capacity": _to_float((raw or {}).get("action_capacity", 0.0), 0.0),
        "recovery_need": _to_float((raw or {}).get("recovery_need", 0.0), 0.0),
        "survival_pressure": _to_float((raw or {}).get("survival_pressure", 0.0), 0.0),
    }


# --------------------------------------------------
# LOAD
# --------------------------------------------------
def load_memory_state(bot, path: str | None = None) -> dict:

    state = read_memory_state(path)
    return apply_memory_state(bot, state)


# --------------------------------------------------
# SAVE
# --------------------------------------------------
def save_memory_state(bot, path: str | None = None, include_runtime_state: bool | None = None) -> dict | None:

    if bot is None:
        return None

    filepath = _memory_state_path(path)

    if include_runtime_state is None:
        include_runtime_state = bool(getattr(Config, "MCM_SAVE_RUNTIME_STATE", True))

    payload = build_memory_state(bot, include_runtime_state=bool(include_runtime_state))

    try:
        _ensure_dir(filepath)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        return None

    return payload