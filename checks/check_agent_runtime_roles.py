from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import agent_runtime as ar
from agent_runtime_roles import apply_agent_runtime_role_patch


# ==================================================
# check_agent_runtime_roles.py
# ==================================================
# LOCAL AGENT ROLE CONTRACT CHECK
# ==================================================


# --------------------------------------------------
# CHECK HELPERS
# --------------------------------------------------
def _assert_equal(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def _report(name: str, signal: ar.AgentSignal, score: int, blocking: bool = False) -> ar.AgentReport:
    return ar.AgentReport(
        agent_name=name,
        function="role check",
        signal=signal,
        score=score,
        reads="check",
        message="check",
        blocking=blocking,
    )


# --------------------------------------------------
# ROLE CONTRACT CHECK
# --------------------------------------------------
def check_roles() -> None:
    apply_agent_runtime_role_patch()
    cases = {
        "BOS / CHoCH Agent": "structure",
        "LL / HH Box Agent": "structure",
        "Support / Resistance Agent": "structure",
        "Breakout / Fakeout Agent": "structure",
        "MACD Agent": "momentum",
        "RSI Agent": "momentum",
        "VWAP Agent": "momentum",
        "Volume Agent": "context",
        "Volatility Regime Agent": "risk",
        "Risk Agent": "risk",
        "CEO Agent": "decision",
    }
    for name, role in cases.items():
        _assert_equal(name, ar._agent_role(name), role)


# --------------------------------------------------
# CEO CONTRACT CHECK
# --------------------------------------------------
def check_ceo() -> None:
    apply_agent_runtime_role_patch()
    reports = [
        _report("BOS / CHoCH Agent", "LONG", 76),
        _report("MACD Agent", "LONG", 78),
        _report("Volume Agent", "LONG", 80),
        _report("Risk Agent", "NEUTRAL", 70),
    ]
    ceo = ar._ceo_agent(reports)
    _assert_equal("CEO signal", ceo.signal, "LONG")
    _assert_equal("CEO decision role", ceo.role, "decision")
    _assert_equal("Context role present", ceo.details["role_groups"]["context"]["long_count"], 1)

    blocked = ar._ceo_agent(reports + [_report("Risk Agent", "NEUTRAL", 10, blocking=True)])
    _assert_equal("CEO blocked signal", blocked.signal, "NEUTRAL")
    _assert_equal("CEO blocked flag", blocked.blocking, True)
    _assert_equal("CEO blocked decision", blocked.details["decision"], "BLOCKED")


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    check_roles()
    check_ceo()
    print("Agent runtime role checks OK")


if __name__ == "__main__":
    main()
