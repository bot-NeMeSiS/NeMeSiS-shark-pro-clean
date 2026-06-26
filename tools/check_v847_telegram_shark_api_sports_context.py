from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
shark = (ROOT / "engines" / "shark_ai_product_assistant_engine.py").read_text(encoding="utf-8", errors="replace")
telegram = (ROOT / "engines" / "telegram_quality_filter_engine.py").read_text(encoding="utf-8", errors="replace")

checks = {
    "shark_context_gets_provider": "api_sports_provider" in app and "explain_api_sports_provider_state" in app,
    "shark_no_hallucination_kept": "Cuotas pendientes" in shark and "No recomiendo forzar una entrada" in shark,
    "telegram_quality_kept": "filter_telegram_candidates" in app and "skipped_low_quality" in telegram.lower(),
    "no_real_send_from_provider": "send_message" not in (ROOT / "engines" / "api_sports_provider_engine.py").read_text(encoding="utf-8", errors="replace"),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
