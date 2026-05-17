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
# DASHBOARD ROLE PATCH
# --------------------------------------------------
def prepare_dashboard_role_patch() -> str:
    root = Path(__file__).resolve().parents[1]
    dashboard_path = root / "dashboard.html"
    patch_path = root / "ui" / "patches" / "dashboard_agent_roles_patch.js"
    marker_start = "<!-- dashboard_agent_roles_patch.js:start -->"
    marker_end = "<!-- dashboard_agent_roles_patch.js:end -->"

    if not dashboard_path.exists():
        return "SKIP dashboard.html fehlt"
    if not patch_path.exists():
        return "SKIP ui/patches/dashboard_agent_roles_patch.js fehlt"

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
    elif "dashboard_agent_roles_patch.js" in html:
        legacy_pattern = re.compile(
            r"\n?<!-- dashboard_agent_roles_patch\.js -->\n<script>\n.*?\n</script>\n?",
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
        raise RuntimeError("Dashboard-Rollenpatch konnte nicht verifiziert werden")
    return f"{action} ui/patches/dashboard_agent_roles_patch.js {version}"


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    result = prepare_dashboard_role_patch()
    print(f"Dashboard Runtime: {result}")


if __name__ == "__main__":
    main()
