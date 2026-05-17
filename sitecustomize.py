from __future__ import annotations

try:
    from agent_runtime_roles import apply_agent_runtime_role_patch

    apply_agent_runtime_role_patch()
except Exception:
    pass

try:
    from brain_replay_enhancements import apply_brain_replay_enhancement_patch

    apply_brain_replay_enhancement_patch()
except Exception:
    pass
