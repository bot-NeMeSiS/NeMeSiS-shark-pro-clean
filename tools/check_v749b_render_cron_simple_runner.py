from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V749B_RENDER_CRON_SIMPLE_RUNNER_FINAL_FIX"
RUNNER = ROOT / "tools" / "render_cron_telegram_tick.py"
SETUP = ROOT / "reports" / "V749B_RENDER_CRON_SIMPLE_RUNNER_SETUP.md"
REPORT = ROOT / "reports" / "V749B_RENDER_CRON_SIMPLE_RUNNER_FINAL_FIX_REPORT.md"


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    current_version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    assert_true(current_version in {VERSION, "V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH"}, "VERSION.txt no contiene V749B/V750.")
    assert_true(RUNNER.exists(), "Falta tools/render_cron_telegram_tick.py")
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)

    for needle in (
        "PUBLIC_BASE_URL",
        "AUTOMATION_SECRET",
        "/api/automation/telegram/tick",
        "urllib.request",
        "mask_secret",
        "MISSING_PUBLIC_BASE_URL",
        "MISSING_AUTOMATION_SECRET",
        "AUTOMATION_SECRET_INVALID",
        "Europe/Madrid",
        "return 0 if status == 200",
    ):
        assert_true(needle in source, f"Falta {needle} en runner")

    assert_true("requests" not in source, "El runner no debe depender de requests.")
    assert_true("curl" not in source.lower() or "no usar curl" not in source.lower(), "El runner no debe ejecutar curl.")
    assert_true("print(url" not in source and "print_event(url" not in source, "No imprimir URL con secret completo.")

    setup = SETUP.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    for doc, name in ((setup, "setup"), (report, "report")):
        assert_true("python tools/render_cron_telegram_tick.py" in doc, f"Falta command simple en {name}.")
        assert_true("PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com" in doc, f"Falta PUBLIC_BASE_URL en {name}.")
        assert_true("AUTOMATION_SECRET" in doc, f"Falta AUTOMATION_SECRET en {name}.")

    build = (ROOT / "tools" / "build_clean_release.py").read_text(encoding="utf-8")
    assert_true("reports/V749B_" in build, "build_clean_release debe incluir reports V749B.")

    print("V749B Render Cron simple runner check OK")


if __name__ == "__main__":
    main()
