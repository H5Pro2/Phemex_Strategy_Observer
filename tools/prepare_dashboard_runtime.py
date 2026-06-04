from __future__ import annotations

import re
from pathlib import Path


# ==================================================
# tools/prepare_dashboard_runtime.py
# ==================================================
# LOCAL DASHBOARD RUNTIME PREPARATION
# ==================================================


# --------------------------------------------------
# PATCH VERSION
# --------------------------------------------------
def dashboard_patch_version(patch: str) -> str:
    match = re.search(r"PATCH_VERSION\s*=\s*['\"]([^'\"]+)['\"]", patch)
    return match.group(1) if match else "unknown"


# --------------------------------------------------
# PATCH INJECTION
# --------------------------------------------------
def inject_dashboard_patch(dashboard_path: Path, patch_path: Path, patch_name: str) -> str:
    marker_start = f"<!-- {patch_name}:start -->"
    marker_end = f"<!-- {patch_name}:end -->"

    if not dashboard_path.exists():
        return f"SKIP dashboard.html fehlt"
    if not patch_path.exists():
        return f"SKIP {patch_path.as_posix()} fehlt"

    html = dashboard_path.read_text(encoding="utf-8")
    patch = patch_path.read_text(encoding="utf-8")
    version = dashboard_patch_version(patch)
    block = f"\n{marker_start}\n<script>\n{patch}\n</script>\n{marker_end}\n"

    pattern = re.compile(
        re.escape(marker_start) + r".*?" + re.escape(marker_end),
        re.DOTALL,
    )
    if pattern.search(html):
        html = pattern.sub(block.strip(), html)
        action = "UPDATED"
    elif patch_name in html:
        legacy_pattern = re.compile(
            rf"\n?<!-- {re.escape(patch_name)} -->\n<script>\n.*?\n</script>\n?",
            re.DOTALL,
        )
        html = legacy_pattern.sub("", html)
        if "</body>" in html:
            html = html.replace("</body>", block + "</body>")
        else:
            html = html + block
        action = "MIGRATED"
    elif "</body>" in html:
        html = html.replace("</body>", block + "</body>")
        action = "ADDED"
    else:
        html = html + block
        action = "APPENDED"

    dashboard_path.write_text(html, encoding="utf-8")
    verify_html = dashboard_path.read_text(encoding="utf-8")
    if version not in verify_html or marker_start not in verify_html or marker_end not in verify_html:
        raise RuntimeError(f"Dashboard-Patch konnte nicht verifiziert werden: {patch_name}")
    return f"{action} {patch_path.as_posix()} {version}"


# --------------------------------------------------
# DASHBOARD PATCHES
# --------------------------------------------------
def prepare_dashboard_patches() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    dashboard_path = root / "dashboard.html"
    patches = [
        (root / "ui" / "patches" / "dashboard_agent_roles_patch.js", "dashboard_agent_roles_patch.js"),
        (root / "ui" / "patches" / "dashboard_chart_pane_patch.js", "dashboard_chart_pane_patch.js"),
        (root / "ui" / "patches" / "dashboard_kline_native_indicators_patch.js", "dashboard_kline_native_indicators_patch.js"),
        (root / "ui" / "patches" / "dashboard_all_agent_indicators_patch.js", "dashboard_all_agent_indicators_patch.js"),
        (root / "ui" / "patches" / "dashboard_direct_agent_chart_view_fix_patch.js", "dashboard_direct_agent_chart_view_fix_patch.js"),
        (root / "ui" / "patches" / "dashboard_agent_setup_cleanup_patch.js", "dashboard_agent_setup_cleanup_patch.js"),
        (root / "ui" / "patches" / "dashboard_settings_layout_patch.js", "dashboard_settings_layout_patch.js"),
        (root / "ui" / "patches" / "dashboard_settings_tabs_patch.js", "dashboard_settings_tabs_patch.js"),
        (root / "ui" / "patches" / "dashboard_agent_setup_final_order_patch.js", "dashboard_agent_setup_final_order_patch.js"),
        (root / "ui" / "patches" / "dashboard_chart_status_layout_fix_patch.js", "dashboard_chart_status_layout_fix_patch.js"),
        (root / "ui" / "patches" / "dashboard_chart_view_focus_patch.js", "dashboard_chart_view_focus_patch.js"),
        (root / "ui" / "patches" / "dashboard_tradingview_overlay_patch.js", "dashboard_tradingview_overlay_patch.js"),
        (root / "ui" / "patches" / "dashboard_chart_view_controls_patch.js", "dashboard_chart_view_controls_patch.js"),
        (root / "ui" / "patches" / "dashboard_bot_view_layout_patch.js", "dashboard_bot_view_layout_patch.js"),
    ]
    return [inject_dashboard_patch(dashboard_path, patch_path, patch_name) for patch_path, patch_name in patches]


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    results = prepare_dashboard_patches()
    for result in results:
        print(f"Dashboard Runtime: {result}")


if __name__ == "__main__":
    main()
