from pathlib import Path

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
errors = []


def text(relative):
    path = ROOT / relative
    if not path.exists():
        errors.append(f"missing:{relative}")
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


if (ROOT / "VERSION.txt").read_bytes().startswith(b"\xef\xbb\xbf"):
    errors.append("VERSION.txt:BOM")
if text("VERSION.txt").strip() != VERSION or text("APP_VERSION").strip() != VERSION:
    errors.append("version_identity")

app_source = text("app.py")
base_source = text("templates/base.html")
component = text("templates/components/v937_sports_lifecycle.html")
ui = text("templates/components/v933_ui.html")

for marker in (
    "get_v937_nemesis_data_confidence",
    "get_v937_attention_priority",
    "get_v937_pick_learning",
    "Mide calidad del dato, no probabilidad de ganar",
    "NEMESIS_CACHE_V937",
):
    if marker not in app_source:
        errors.append(f"app:{marker}")

for marker in (
    "data_confidence_badge",
    "data_confidence_panel",
    "attention_priority",
    "lifecycle_story",
    "professional_pick_brief",
    "learning_receipt",
):
    if marker not in component:
        errors.append(f"component:{marker}")

for marker in ("data_confidence_badge(match", "data_confidence_badge(pick", "attention_priority(match"):
    if marker not in ui:
        errors.append(f"cards:{marker}")

for asset in ("v937-sports-lifecycle.css", "v937-sports-lifecycle.js"):
    if base_source.count(asset) != 1:
        errors.append(f"base_asset:{asset}")

template_markers = {
    "templates/calendar.html": "lifecycle_story",
    "templates/live.html": "lifecycle_story",
    "templates/picks.html": "data_confidence_panel",
    "templates/match_detail.html": "data_confidence_panel",
    "templates/track_record.html": "learning_receipt",
    "templates/shark.html": "no recomiendo una selección hoy",
    "templates/admin_data_trust_center.html": "Índice de Confianza NeMeSiS",
}
for path, marker in template_markers.items():
    if marker not in text(path):
        errors.append(f"template:{path}:{marker}")

if "pixel_perfect_claim_allowed\": True" in app_source:
    errors.append("unsafe_pixel_perfect_claim")

environment = Environment()
for path in sorted((ROOT / "templates").rglob("*.html")):
    try:
        environment.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"jinja:{path.relative_to(ROOT)}:{type(exc).__name__}")

if errors:
    print("V937 SPORTS LIFECYCLE CHECK: FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("V937 SPORTS LIFECYCLE CHECK: OK")
