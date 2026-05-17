from __future__ import annotations

from pathlib import Path
import re


# ==================================================
# check_dashboard_runtime_patches.py
# ==================================================
# LOCAL DASHBOARD PATCH STRUCTURE CHECK
# ==================================================


# --------------------------------------------------
# PATCH CONFIG
# --------------------------------------------------
REQUIRED_PATCHES = [
    "dashboard_agent_roles_patch.js",
    "dashboard_chart_pane_patch.js",
    "dashboard_kline_native_indicators_patch.js",
    "dashboard_agent_setup_cleanup_patch.js",
]


# --------------------------------------------------
# CHECKS
# --------------------------------------------------
def patch_version(content: str) -> str:
    match = re.search(r"PATCH_VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    return match.group(1) if match else ""


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    patch_dir = root / "ui" / "patches"
    dashboard = root / "dashboard.html"

    if not dashboard.exists():
        raise AssertionError("dashboard.html fehlt")

    dashboard_html = dashboard.read_text(encoding="utf-8")
    for patch_name in REQUIRED_PATCHES:
        patch_path = patch_dir / patch_name
        if not patch_path.exists():
            raise AssertionError(f"Patch fehlt: {patch_path.as_posix()}")
        content = patch_path.read_text(encoding="utf-8")
        version = patch_version(content)
        if not version:
            raise AssertionError(f"PATCH_VERSION fehlt: {patch_name}")
        if f"<!-- {patch_name}:start -->" not in dashboard_html:
            raise AssertionError(f"Dashboard Marker fehlt: {patch_name}:start")
        if f"<!-- {patch_name}:end -->" not in dashboard_html:
            raise AssertionError(f"Dashboard Marker fehlt: {patch_name}:end")
        if version not in dashboard_html:
            raise AssertionError(f"Dashboard Version fehlt: {patch_name} {version}")

    print("Dashboard runtime patch checks OK")


if __name__ == "__main__":
    main()
