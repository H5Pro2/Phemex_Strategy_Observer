from __future__ import annotations

try:
    from agent_runtime_roles import apply_agent_runtime_role_patch

    apply_agent_runtime_role_patch()
except Exception:
    pass
