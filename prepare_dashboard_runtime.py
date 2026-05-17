from __future__ import annotations

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
    marker = "dashboard_agent_roles_patch.js"

    if not dashboard_path.exists() or not patch_path.exists():
        return

    html = dashboard_path.read_text(encoding="utf-8")
    if marker in html:
        return

    patch = patch_path.read_text(encoding="utf-8")
    block = "\n<!-- dashboard_agent_roles_patch.js -->\n<script>\n" + patch + "\n</script>\n"
    if "</body>" in html:
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
