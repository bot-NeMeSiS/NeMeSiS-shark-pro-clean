from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / "static/v933_design_tokens.css",
    ROOT / "static/v937-product-client.css",
    ROOT / "static/v937-product-client.js",
    ROOT / "reports/V937_PRODUCT_UPDATE_CLIENT_01.md",
]
missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
base = ROOT / "templates/base.html"
errors = list(missing)
current_version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
app_version = (ROOT / "APP_VERSION").read_text(encoding="utf-8-sig").strip()
version_match = re.fullmatch(r"V(\d+)(?:_[A-Z0-9]+)*", current_version)
if not version_match or int(version_match.group(1)) < 937:
    errors.append("VERSION.txt")
if app_version != current_version:
    errors.append("APP_VERSION")
text = base.read_text(encoding="utf-8", errors="ignore") if base.exists() else ""
for marker in ("v937-product-client.css", "v937-product-client.js"):
    if text.count(marker) != 1:
        errors.append(f"base link count: {marker}")
if "letter-spacing:-" in (ROOT / "static/v937-product-client.css").read_text(encoding="utf-8"):
    errors.append("negative letter spacing")
gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
if "!static/v933_design_tokens.css" not in gitignore_text:
    errors.append("v933 design tokens gitignore exception")
app_text = (ROOT / "app.py").read_text(encoding="utf-8", errors="ignore")
unsafe_runtime_read = '"has_v933_accessibility_pass": "focus-visible" in (BASE_DIR / "static" / "v933_design_tokens.css").read_text' in app_text
if unsafe_runtime_read:
    errors.append("unsafe runtime design tokens read")
if errors:
    print("V937 CLIENT UPDATE CHECK: FAIL", errors)
    raise SystemExit(1)
print("V937 CLIENT UPDATE CHECK: OK")
