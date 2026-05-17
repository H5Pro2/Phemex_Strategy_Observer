from __future__ import annotations

import re
from pathlib import Path


# ==================================================
# prepare_dashboard_runtime.py
# ==================================================
# LOCAL DASHBOARD RUNTIME PREPARATION
# ==================================================


# --------------------------------------------------
# DASHBOARD ROLE PATCH
# --------------------------------------------------
def prepare_dashboard_role_patch() -> None:
    root = Path(__file__).resolve().parent
    dashboard_path = root / "dashboard.html"
    patch_path = root / "dashboard_agent_roles_patch.js"
    marker_start = "<!-- dashboard_agent_roles_patch.js:start -->"
    marker_end = "<!-- dashboard_agent_roles_patch.js:end -->"

    if not dashboard_path.exists() or not patch_path.exists():
        return

    html = dashboard_path.read_text(encoding="utf-8")
    patch = patch_path.read_text(encoding="utf-8")
    block = f"\n{marker_start}\n<script>\n{patch}\n</script>\n{marker_end}\n"

    pattern = re.compile(
        re.escape(marker_start) + r".*?" + re.escape(marker_end),
        re.DOTALL,
    )
    if pattern.search(html):
        html = pattern.sub(block.strip(), html)
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
    elif "</body>" in html:
        html = html.replace("</body>", block + "</body>")
    else:
        html = html + block

    dashboard_path.write_text(html, encoding="utf-8")


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    prepare_dashboard_role_patch()


if __name__ == "__main__":
    main()
