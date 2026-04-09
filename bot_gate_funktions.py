# ==================================================
# bot_gate_funktions.py
# Entry / Gate / Strategie Mechanik außerhalb von bot.py
# ==================================================
from config import Config
from debug_reader import dbr_debug
from MCM_Brain_Modell import build_runtime_decision_tendency, decide_mcm_brain_entry


DEBUG = True
# --------------------------------------------------
def evaluate_entry_decision(bot, window, candle_state):

    tendency_state = build_runtime_decision_tendency(
        window=window,
        candle_state=candle_state,
        bot=bot,
    )

    if tendency_state is None:
        return None

    decision_tendency = str(tendency_state.get("decision_tendency", "hold") or "hold").strip().lower()

    if decision_tendency != "act":
        return {
            "decision_tendency": str(decision_tendency or "hold"),
            "proposed_decision": str(tendency_state.get("proposed_decision", "WAIT") or "WAIT"),
            "self_state": str(tendency_state.get("self_state", "stable") or "stable"),
            "attractor": str(tendency_state.get("attractor", "neutral") or "neutral"),
            "focus": dict(tendency_state.get("focus", {}) or {}),
            "world_state": dict(tendency_state.get("world_state", {}) or {}),
            "structure_perception_state": dict(tendency_state.get("structure_perception_state", {}) or {}),
            "outer_visual_perception_state": dict(tendency_state.get("outer_visual_perception_state", {}) or {}),
            "inner_field_perception_state": dict(tendency_state.get("inner_field_perception_state", {}) or {}),
            "perception_state": dict(tendency_state.get("perception_state", {}) or {}),
            "processing_state": dict(tendency_state.get("processing_state", {}) or {}),
            "felt_state": dict(tendency_state.get("felt_state", {}) or {}),
            "thought_state": dict(tendency_state.get("thought_state", {}) or {}),
            "meta_regulation_state": dict(tendency_state.get("meta_regulation_state", {}) or {}),
            "expectation_state": dict(tendency_state.get("expectation_state", {}) or {}),
            "state_signature": dict(tendency_state.get("state_signature", {}) or {}),
            "signature_bias": float(tendency_state.get("signature_bias", 0.0) or 0.0),
            "signature_block": bool(tendency_state.get("signature_block", False)),
            "signature_quality": float(tendency_state.get("signature_quality", 0.0) or 0.0),
            "signature_distance": float(tendency_state.get("signature_distance", 0.0) or 0.0),
            "context_cluster_id": str(tendency_state.get("context_cluster_id", "-") or "-"),
            "context_cluster_bias": float(tendency_state.get("context_cluster_bias", 0.0) or 0.0),
            "context_cluster_quality": float(tendency_state.get("context_cluster_quality", 0.0) or 0.0),
            "context_cluster_distance": float(tendency_state.get("context_cluster_distance", 0.0) or 0.0),
            "context_cluster_block": bool(tendency_state.get("context_cluster_block", False)),
            "inhibition_level": float(tendency_state.get("inhibition_level", 0.0) or 0.0),
            "habituation_level": float(tendency_state.get("habituation_level", 0.0) or 0.0),
            "competition_bias": float(tendency_state.get("competition_bias", 0.0) or 0.0),
            "observation_mode": bool(tendency_state.get("observation_mode", False)),
            "long_score": float(tendency_state.get("long_score", 0.0) or 0.0),
            "short_score": float(tendency_state.get("short_score", 0.0) or 0.0),
            "field_density": float(tendency_state.get("field_density", 0.0) or 0.0),
            "field_stability": float(tendency_state.get("field_stability", 0.0) or 0.0),
            "regulatory_load": float(tendency_state.get("regulatory_load", 0.0) or 0.0),
            "action_capacity": float(tendency_state.get("action_capacity", 0.0) or 0.0),
            "recovery_need": float(tendency_state.get("recovery_need", 0.0) or 0.0),
            "survival_pressure": float(tendency_state.get("survival_pressure", 0.0) or 0.0),
            "rejection_reason": str(tendency_state.get("rejection_reason", "runtime_non_action") or "runtime_non_action"),
        }

    decision = decide_mcm_brain_entry(
        window=window,
        candle_state=candle_state,
        bot=bot,
    )

    if decision is None:
        return {
            "decision_tendency": "replan",
            "proposed_decision": str(tendency_state.get("proposed_decision", "WAIT") or "WAIT"),
            "self_state": str(tendency_state.get("self_state", "stable") or "stable"),
            "attractor": str(tendency_state.get("attractor", "neutral") or "neutral"),
            "focus": dict(tendency_state.get("focus", {}) or {}),
            "world_state": dict(tendency_state.get("world_state", {}) or {}),
            "structure_perception_state": dict(tendency_state.get("structure_perception_state", {}) or {}),
            "outer_visual_perception_state": dict(tendency_state.get("outer_visual_perception_state", {}) or {}),
            "inner_field_perception_state": dict(tendency_state.get("inner_field_perception_state", {}) or {}),
            "perception_state": dict(tendency_state.get("perception_state", {}) or {}),
            "processing_state": dict(tendency_state.get("processing_state", {}) or {}),
            "felt_state": dict(tendency_state.get("felt_state", {}) or {}),
            "thought_state": dict(tendency_state.get("thought_state", {}) or {}),
            "meta_regulation_state": dict(tendency_state.get("meta_regulation_state", {}) or {}),
            "expectation_state": dict(tendency_state.get("expectation_state", {}) or {}),
            "state_signature": dict(tendency_state.get("state_signature", {}) or {}),
            "signature_bias": float(tendency_state.get("signature_bias", 0.0) or 0.0),
            "signature_block": bool(tendency_state.get("signature_block", False)),
            "signature_quality": float(tendency_state.get("signature_quality", 0.0) or 0.0),
            "signature_distance": float(tendency_state.get("signature_distance", 0.0) or 0.0),
            "context_cluster_id": str(tendency_state.get("context_cluster_id", "-") or "-"),
            "context_cluster_bias": float(tendency_state.get("context_cluster_bias", 0.0) or 0.0),
            "context_cluster_quality": float(tendency_state.get("context_cluster_quality", 0.0) or 0.0),
            "context_cluster_distance": float(tendency_state.get("context_cluster_distance", 0.0) or 0.0),
            "context_cluster_block": bool(tendency_state.get("context_cluster_block", False)),
            "inhibition_level": float(tendency_state.get("inhibition_level", 0.0) or 0.0),
            "habituation_level": float(tendency_state.get("habituation_level", 0.0) or 0.0),
            "competition_bias": float(tendency_state.get("competition_bias", 0.0) or 0.0),
            "observation_mode": bool(tendency_state.get("observation_mode", False)),
            "long_score": float(tendency_state.get("long_score", 0.0) or 0.0),
            "short_score": float(tendency_state.get("short_score", 0.0) or 0.0),
            "field_density": float(tendency_state.get("field_density", 0.0) or 0.0),
            "field_stability": float(tendency_state.get("field_stability", 0.0) or 0.0),
            "regulatory_load": float(tendency_state.get("regulatory_load", 0.0) or 0.0),
            "action_capacity": float(tendency_state.get("action_capacity", 0.0) or 0.0),
            "recovery_need": float(tendency_state.get("recovery_need", 0.0) or 0.0),
            "survival_pressure": float(tendency_state.get("survival_pressure", 0.0) or 0.0),
            "rejection_reason": "decision_plan_missing",
        }

    side = str(decision.get("decision", "")).upper().strip()
    entry_price = float(decision.get("entry_price", 0.0) or 0.0)
    sl_price = float(decision.get("sl_price", 0.0) or 0.0)
    tp_price = float(decision.get("tp_price", 0.0) or 0.0)
    rr_value = float(decision.get("rr_value", 0.0) or 0.0)

    if side not in ("LONG", "SHORT"):
        return None

    if entry_price <= 0.0 or sl_price <= 0.0 or tp_price <= 0.0:
        return None

    risk = abs(entry_price - sl_price)
    if risk <= 0.0:
        return None

    if rr_value <= 0.0:
        rr_value = abs(tp_price - entry_price) / risk

    focus = dict(decision.get("focus", {}) or {})
    filtered_vision = dict(decision.get("filtered_vision", {}) or {})
    raw_vision = dict(decision.get("vision", {}) or {})
    state_signature = dict(decision.get("state_signature", {}) or {})
    perception_state = dict(decision.get("perception_state", {}) or {})
    felt_state = dict(decision.get("felt_state", {}) or {})
    thought_state = dict(decision.get("thought_state", {}) or {})
    meta_regulation_state = dict(decision.get("meta_regulation_state", {}) or {})
    expectation_state = dict(decision.get("expectation_state", {}) or {})

    if DEBUG:
        dbr_debug(
            f"MCM_ENTRY | side={side} entry={entry_price:.6f} sl={sl_price:.6f} tp={tp_price:.6f} rr={rr_value:.4f} "
            f"self_state={decision.get('self_state', '-')} attractor={decision.get('attractor', '-')} "
            f"memory_center={float(decision.get('memory_center', 0.0) or 0.0):.4f} "
            f"memory_strength={int(decision.get('memory_strength', 0) or 0)} "
            f"focus_direction={float(focus.get('focus_direction', 0.0) or 0.0):.4f} "
            f"focus_strength={float(focus.get('focus_strength', 0.0) or 0.0):.4f} "
            f"focus_confidence={float(focus.get('focus_confidence', 0.0) or 0.0):.4f} "
            f"target_lock={float(focus.get('target_lock', 0.0) or 0.0):.4f} "
            f"noise_damp={float(focus.get('noise_damp', 0.0) or 0.0):.4f} "
            f"signal_relevance={float(focus.get('signal_relevance', 0.0) or 0.0):.4f} "
            f"entry_expectation={float(expectation_state.get('entry_expectation', 0.0) or 0.0):.4f} "
            f"target_expectation={float(expectation_state.get('target_expectation', 0.0) or 0.0):.4f} "
            f"approach_pressure={float(expectation_state.get('approach_pressure', 0.0) or 0.0):.4f} "
            f"pressure_release={float(expectation_state.get('pressure_release', 0.0) or 0.0):.4f} "
            f"experience_regulation={float(expectation_state.get('experience_regulation', 0.0) or 0.0):.4f} "
            f"reflection_maturity={float(expectation_state.get('reflection_maturity', 0.0) or 0.0):.4f} "
            f"signature_key={str(state_signature.get('signature_key', '-'))} "
            f"signature_bias={float(decision.get('signature_bias', 0.0) or 0.0):.4f} "
            f"signature_block={bool(decision.get('signature_block', False))} "
            f"signature_quality={float(decision.get('signature_quality', 0.0) or 0.0):.4f} "
            f"signature_distance={float(decision.get('signature_distance', 0.0) or 0.0):.4f} "
            f"context_cluster_id={str(decision.get('context_cluster_id', '-'))} "
            f"context_cluster_bias={float(decision.get('context_cluster_bias', 0.0) or 0.0):.4f} "
            f"context_cluster_quality={float(decision.get('context_cluster_quality', 0.0) or 0.0):.4f} "
            f"context_cluster_distance={float(decision.get('context_cluster_distance', 0.0) or 0.0):.4f} "
            f"context_cluster_block={bool(decision.get('context_cluster_block', False))} "
            f"inhibition_level={float(decision.get('inhibition_level', 0.0) or 0.0):.4f} "
            f"habituation_level={float(decision.get('habituation_level', 0.0) or 0.0):.4f} "
            f"competition_bias={float(decision.get('competition_bias', 0.0) or 0.0):.4f} "
            f"observation_mode={bool(decision.get('observation_mode', False))} "
            f"long_score={float(decision.get('long_score', 0.0) or 0.0):.4f} "
            f"short_score={float(decision.get('short_score', 0.0) or 0.0):.4f}",
            "entry_debug.csv",
        )

    return {
        "decision_tendency": "act",
        "decision": side,
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "rr_value": rr_value,
        "energy": float(decision.get("energy", 0.0) or 0.0),
        "coherence": float(decision.get("coherence", 0.0) or 0.0),
        "asymmetry": int(decision.get("asymmetry", 0) or 0),
        "coh_zone": float(decision.get("coh_zone", 0.0) or 0.0),
        "self_state": str(decision.get("self_state", "stable")),
        "attractor": str(decision.get("attractor", "neutral")),
        "memory_center": float(decision.get("memory_center", 0.0) or 0.0),
        "memory_strength": int(decision.get("memory_strength", 0) or 0),
        "vision": raw_vision,
        "filtered_vision": filtered_vision,
        "focus": focus,
        "world_state": dict(decision.get("world_state", {}) or {}),
        "structure_perception_state": dict(decision.get("structure_perception_state", {}) or {}),
        "outer_visual_perception_state": dict(decision.get("outer_visual_perception_state", {}) or {}),
        "inner_field_perception_state": dict(decision.get("inner_field_perception_state", {}) or {}),
        "processing_state": dict(decision.get("processing_state", {}) or {}),
        "perception_state": perception_state,
        "felt_state": felt_state,
        "thought_state": thought_state,
        "meta_regulation_state": meta_regulation_state,
        "expectation_state": expectation_state,
        "state_signature": state_signature,
        "entry_expectation": float(expectation_state.get("entry_expectation", 0.0) or 0.0),
        "target_expectation": float(expectation_state.get("target_expectation", 0.0) or 0.0),
        "approach_pressure": float(expectation_state.get("approach_pressure", 0.0) or 0.0),
        "pressure_release": float(expectation_state.get("pressure_release", 0.0) or 0.0),
        "experience_regulation": float(expectation_state.get("experience_regulation", 0.0) or 0.0),
        "reflection_maturity": float(expectation_state.get("reflection_maturity", 0.0) or 0.0),
        "entry_validity_band": dict(decision.get("entry_validity_band", {}) or {}),
        "target_conviction": float(decision.get("target_conviction", 0.0) or 0.0),
        "risk_model_score": float(decision.get("risk_model_score", 0.0) or 0.0),
        "reward_model_score": float(decision.get("reward_model_score", 0.0) or 0.0),
        "signature_bias": float(decision.get("signature_bias", 0.0) or 0.0),
        "signature_block": bool(decision.get("signature_block", False)),
        "signature_quality": float(decision.get("signature_quality", 0.0) or 0.0),
        "signature_distance": float(decision.get("signature_distance", 0.0) or 0.0),
        "context_cluster_id": str(decision.get("context_cluster_id", "-") or "-"),
        "context_cluster_bias": float(decision.get("context_cluster_bias", 0.0) or 0.0),
        "context_cluster_quality": float(decision.get("context_cluster_quality", 0.0) or 0.0),
        "context_cluster_distance": float(decision.get("context_cluster_distance", 0.0) or 0.0),
        "context_cluster_block": bool(decision.get("context_cluster_block", False)),
        "inhibition_level": float(decision.get("inhibition_level", 0.0) or 0.0),
        "habituation_level": float(decision.get("habituation_level", 0.0) or 0.0),
        "competition_bias": float(decision.get("competition_bias", 0.0) or 0.0),
        "observation_mode": bool(decision.get("observation_mode", False)),
        "long_score": float(decision.get("long_score", 0.0) or 0.0),
        "short_score": float(decision.get("short_score", 0.0) or 0.0),
    }