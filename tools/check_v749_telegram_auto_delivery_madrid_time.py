from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V749_TELEGRAM_AUTO_DELIVERY_MADRID_TIME_PRODUCTION_FIX"
sys.path.insert(0, str(ROOT))


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    assert_true((ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION, "VERSION.txt no contiene V749.")
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    telegram_source = (ROOT / "engines" / "telegram_delivery_engine.py").read_text(encoding="utf-8")
    madrid_source = (ROOT / "engines" / "madrid_time_engine.py").read_text(encoding="utf-8")

    for needle in (
        "/api/automation/telegram/tick",
        "automation_cron_access_allowed",
        "automatic_cron",
        "manual_admin",
        "last_automation_tick_madrid",
        "sent_at_madrid",
        "QUEUE_EMPTY",
        "NO_DUE_JOBS",
    ):
        assert_true(needle in source, f"Falta {needle} en app.py")

    assert_true("format_telegram_match_time_madrid" in madrid_source, "Falta helper central Madrid para Telegram.")
    assert_true("format_telegram_match_time_madrid" in telegram_source, "Los builders Telegram no usan helper Madrid.")
    assert_true("return admin_telegram_command_center_page()" in source, "/admin/telegram/diagnostics no usa pantalla visual.")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "v749_check.db")
        os.environ["DB_PATH"] = db_path
        os.environ["AUTOMATION_SECRET"] = "v749-secret"
        os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
        os.environ["TELEGRAM_CHAT_ID"] = "-1001234567890"
        os.environ["ENABLE_TELEGRAM_AUTO"] = "true"
        os.environ["AUTO_SEND_TELEGRAM_PICKS"] = "true"
        app_module = importlib.import_module("app")
        app_module.DB_PATH = db_path
        app_module.init_db()

        def fake_send(chat_id, text, message_type="queue", payload=None):
            return {"ok": True, "sent": True, "status": "SENT", "category": "SENT", "fake": True}

        app_module.telegram_send_http = fake_send

        client = app_module.app.test_client()
        no_secret = client.get("/api/automation/telegram/tick")
        assert_true(no_secret.status_code == 403, "Cron sin secret debe devolver 403.")
        with_secret = client.get("/api/automation/telegram/tick?secret=v749-secret&force=1")
        assert_true(with_secret.status_code == 200, "Cron con secret debe devolver 200.")
        payload = with_secret.get_json() or {}
        assert_true(payload.get("automation_source") == "cron", "Cron debe identificarse como fuente cron.")
        assert_true(payload.get("now_madrid"), "Cron debe devolver hora Madrid.")
        assert_true(payload.get("status") in {"QUEUE_EMPTY", "NO_DUE_JOBS", "NO_SENDABLE_ITEMS", "QUEUE_PROCESSED", "Telegram scheduler ejecutado."}, "Estado Cron poco claro.")

        admin = client.get("/admin/telegram/diagnostics")
        assert_true(admin.status_code in {302, 403}, "Diagnostico admin sin login debe quedar protegido.")

    print("V749 telegram auto delivery madrid time check OK")


if __name__ == "__main__":
    main()
