from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
checks = {
    "v848_block": "V848 SHARK REFERENCE BACKGROUND PC MOBILE START" in css,
    "dot_pattern": "radial-gradient(rgba(113,232,255" in css and "background-size:22px 22px" in css,
    "shark_logo_background": 'url("/static/img/shark-logo.svg")' in css,
    "glow_depth": "drop-shadow" in css and "--v848-cyan" in css,
    "no_overflow": "overflow-x:hidden" in css,
    "shell_flag": "data-v848-shell" in base,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
