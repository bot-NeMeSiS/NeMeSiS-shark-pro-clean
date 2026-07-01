from pathlib import Path
import os, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v849_runtime.db"))
import app as nemesis  # noqa: E402
VERSION = "V849_FULL_COMPANY_VISUAL_PRODUCT_EXPERIENCE_ADVANCEMENT"
CURRENT_OR_NEXT = {VERSION, "V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL"}
d = nemesis.app.test_client().get("/api/runtime-version").get_json() or {}
checks = {
    "app_version": d.get("app_version") in CURRENT_OR_NEXT,
    "version_txt": d.get("version_txt") in CURRENT_OR_NEXT,
    "has_v849": d.get("has_v849_full_company_visual_product_experience") is True,
    "has_v848": d.get("has_v848_reference_shark_visual_pc_mobile") is True,
    "has_v847": d.get("has_v847_company_brain_api_sports_provider_qa") is True,
    "has_v845": d.get("has_v845_shark_ai_product_assistant") is True,
    "has_v844": d.get("has_v844_telegram_quality_filter") is True,
    "has_v818": d.get("has_v818_automation") is True,
    "provider_flags": all(k in d for k in ["api_sports_configured","api_football_configured","the_odds_configured","openai_configured","telegram_configured","automation_secret_configured","db_path","static_app_css_hash","static_app_css_size"]),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed}); raise SystemExit(1 if failed else 0)
