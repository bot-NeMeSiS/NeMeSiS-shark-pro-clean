"""Presentation and transport contracts. Transport is always intercepted locally."""
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import io
import json
import re
import urllib.error

import pytest

from engines import telegram_visual_card_engine as cards
from engines import telegram_message_formatter as fmt
from engines.telegram_activity_engine import _is_live, _is_finished, should_send_highlight_alert


@pytest.mark.parametrize("item,expected", [
    ({"kickoff_iso": "2026-01-10T23:30:00Z"}, "00:30"),
    ({"kickoff_iso": "2026-07-10T23:30:00Z"}, "01:30"),
    ({"kickoff_iso": "2026-03-29T01:30:00Z"}, "03:30"),
    ({"kickoff_iso": "2026-10-25T01:30:00Z"}, "02:30"),
    ({"kickoff_iso": "2026-07-10T19:30:00-04:00"}, "01:30"),
    ({"kickoff_iso": "2026-07-11T08:30:00+09:00"}, "01:30"),
    ({"match_date": "2026-07-11", "match_time": "00:30"}, "00:30"),
    ({"kickoff_iso": "broken"}, "Hora pendiente"),
])
def test_canonical_madrid(item, expected):
    assert expected in fmt.madrid_match_time_label(item)


def test_zero_is_real_missing_is_not_zero():
    assert fmt.score_label({"home_score": 0, "away_score": 0}) == "0–0"
    assert fmt.score_label({}) == "Marcador pendiente"
    assert "0 uds" in fmt.format_pick_message({"stake_units": 0})
    assert "Resultados: 0" in fmt.format_evening_recap_message({"results": 0})
    assert "Sin dato confirmado" in fmt.format_evening_recap_message({})


@pytest.mark.parametrize("value", [None, "", "nan", "inf", -1, 0])
def test_invalid_odds_not_published(value):
    assert fmt._v889_odds_label(value) == "Cuota pendiente"


def test_no_false_live_or_final():
    now = datetime.now(timezone.utc)
    match = {"id": "qa-only", "status": "live", "minute": 45}
    assert not _is_live(match)
    assert "EN DIRECTO" not in fmt.format_live_alert_message(match)
    assert not _is_live({"status": "scheduled", "minute": 45})
    match["live_updated_at"] = now.isoformat()
    assert _is_live(match, now)
    assert "EN DIRECTO" in cards.build_live_visual_card_payload(match)["eyebrow"]
    assert not _is_finished({"status": "FT"})
    assert _is_finished({"status": "FT", "home_score": 0, "away_score": 0})


def test_missing_data_is_honest_for_every_kind():
    assert "en 60 min" not in fmt.format_prematch_message({})
    assert "Medio" not in fmt.format_pick_message({})
    assert "ACERTADO" not in fmt.format_result_message({}, {})
    assert "Ya puedes ver" not in fmt.format_highlight_message({}, {})
    assert "Sin enlace habilitado" == cards.build_highlight_visual_card_payload()["market"]
    assert not should_send_highlight_alert({}, {"video_url": "https://example.org/video", "blocked": True})


class Balanced(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.text = [], ""
    def handle_starttag(self, tag, attrs):
        assert tag in {"b", "i", "a", "code", "pre", "u", "s"}
        self.stack.append(tag)
    def handle_endtag(self, tag):
        assert self.stack.pop() == tag
    def handle_data(self, data):
        self.text += data


@pytest.mark.parametrize("limit", [1024, 3900])
def test_html_limit_balanced_with_entities_and_emoji(limit):
    html = fmt.premium_text_html("🦈 <script>unsafe</script> & \"quoted\"\n" + "🎯 x & y " * 2000, limit)
    parser = Balanced()
    parser.feed(html)
    assert not parser.stack
    assert len(parser.text.encode("utf-16-le")) // 2 <= limit
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://x/admin", "https://x/%61dmin/users", "https://u:p@x/picks", "file:///secret"])
def test_private_or_unsafe_links_rejected(url):
    assert not fmt.public_link(url)


@pytest.mark.parametrize("kind", ["pick_alert", "combi_alert", "live_alert", "result_final", "highlight_available"])
def test_all_visual_cards_render_with_missing_fields(kind, monkeypatch):
    from PIL import Image
    monkeypatch.setenv("TELEGRAM_SEND_LIVE_CARDS", "true")
    card = cards.build_visual_card_for_message(kind, {})
    assert card["ok"], card
    with Image.open(io.BytesIO(card["png_bytes"])) as image:
        assert image.size == (960, 1000)
        assert len(image.getcolors(image.width * image.height)) > 100


def test_safe_local_crest_and_missing_crest(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(cards, "STATIC_ROOT", tmp_path)
    # Technical raster fixture, never represented as an actual team crest.
    Image.new("RGBA", (40, 40), (100, 200, 120, 255)).save(tmp_path / "qa.png")
    assert cards._load_crest("/static/qa.png", 90)[1] == "local_crest"
    assert cards._load_crest("/static/missing.png", 90)[0] is None
    assert cards._load_crest("/static/../outside.png", 90)[0] is None
    assert cards._load_crest("https://external.test/qa.png", 90)[1] == "remote_not_cached"
    (tmp_path / "bad.png").write_bytes(b"not an image")
    assert cards._load_crest("/static/bad.png", 90)[0] is None


def test_renderer_failure_is_text_fallback(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("private/path/secret")
    monkeypatch.setattr(cards, "build_telegram_visual_card_png", fail)
    result = cards.build_visual_card_for_message("pick_alert", {})
    assert result == {"ok": False, "mode": "text_fallback", "fallback_reason": "visual_render_failed"}


def test_missing_pillow_is_text_fallback(monkeypatch):
    monkeypatch.setattr(cards, "build_telegram_visual_card_png", lambda *a: None)
    assert cards.build_visual_card_for_message("pick_alert", {})["fallback_reason"] == "pillow_not_available"


@pytest.fixture
def transport(app_module, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-not-a-real-token")
    calls = []
    monkeypatch.setattr(app_module, "telegram_post_send_message", lambda *a: calls.append("text") or {"sent": True, "ok": True, "status": "SENT"})
    monkeypatch.setattr(app_module, "build_visual_card_for_message", lambda *a: {"ok": True, "mode": "png", "png_bytes": b"qa"})
    return app_module, calls


def test_photo_failure_before_send_falls_back_once(transport, monkeypatch):
    app, calls = transport
    monkeypatch.setattr(app, "build_visual_card_for_message", lambda *a: {"ok": False, "fallback_reason": "visual_render_failed"})
    result = app.telegram_send_http("qa", "<b>Mensaje</b>", payload={"visual_card_type": "pick_alert", "visual_card_enabled": True})
    assert result["sent"] and calls == ["text"]
    assert result["visual_card"]["mode"] == "text_fallback"


def test_photo_timeout_does_not_send_second_message(transport, monkeypatch):
    app, calls = transport
    def fail(*args):
        calls.append("photo")
        raise TimeoutError("private-token-must-not-leak")
    monkeypatch.setattr(app, "telegram_post_send_photo", fail)
    result = app.telegram_send_http("qa", "Mensaje", payload={"visual_card_type": "pick_alert", "visual_card_enabled": True})
    assert result["delivery_uncertain"] and not result["sent"]
    assert calls == ["photo"] and "private-token" not in str(result)


def test_photo_success_sends_only_one(transport, monkeypatch):
    app, calls = transport
    monkeypatch.setattr(app, "telegram_post_send_photo", lambda *a: calls.append("photo") or {"sent": True, "ok": True})
    assert app.telegram_send_http("qa", "Mensaje", payload={"visual_card_type": "pick_alert", "visual_card_enabled": True})["sent"]
    assert calls == ["photo"]


def test_definite_photo_rejection_falls_back_once(transport, monkeypatch):
    app, calls = transport
    def reject(*args):
        calls.append("photo")
        raise urllib.error.HTTPError("https://api.telegram.org/redacted", 400, "Bad Request", {}, io.BytesIO(b'{"ok":false,"description":"Bad Request: IMAGE_PROCESS_FAILED"}'))
    monkeypatch.setattr(app, "telegram_post_send_photo", reject)
    result = app.telegram_send_http("qa", "Mensaje", payload={"visual_card_type": "pick_alert", "visual_card_enabled": True})
    assert result["sent"] and calls == ["photo", "text"]


def test_plain_fallback_after_html_rejection(transport, monkeypatch):
    app, calls = transport
    def send(url, data):
        calls.append(data.copy())
        if "parse_mode" in data:
            raise urllib.error.HTTPError(url, 400, "Bad Request", {}, io.BytesIO(b'{"ok":false,"description":"Bad Request: can\\u0027t parse entities"}'))
        return {"sent": True, "ok": True}
    monkeypatch.setattr(app, "telegram_post_send_message", send)
    result = app.telegram_send_http("qa", "<b>NeMeSiS &amp; SHARK</b>")
    assert result["sent"] and result["retry_plain"]
    assert len(calls) == 2 and calls[1]["text"] == "NeMeSiS & SHARK"
    assert "parse_mode" not in calls[1]


def test_api_rejection_and_empty_body_are_not_success(transport):
    app, calls = transport
    assert not app.telegram_transport_result({"ok": False})["sent"]
    assert app.telegram_transport_result({"ok": True})["delivery_uncertain"]
    assert app.telegram_send_http("qa", "  ")["status"] == "EMPTY_MESSAGE"
    assert calls == []


def test_photo_caption_transport_is_valid_html(app_module, monkeypatch):
    captured = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"ok":true,"result":{"message_id":123}}'
    monkeypatch.setattr(app_module.urllib.request, "urlopen", lambda request, **kw: captured.append(request.data) or Response())
    result = app_module.telegram_post_send_photo("qa-only", "qa", b"png", "<b>" + "x &amp; 🎯 " * 400 + "</b>", {"include_picks_button": False})
    assert result["sent"]
    wire = captured[0].decode("utf-8")
    caption = wire.split('name="caption"\r\n\r\n', 1)[1].split("\r\n--", 1)[0]
    parser = Balanced()
    parser.feed(caption)
    assert not parser.stack
    assert len(parser.text.encode("utf-16-le")) // 2 <= 1024
    assert "Juego responsable" in parser.text


def test_queue_dedup_and_uncertain_delivery_survive_reload(app_module, monkeypatch):
    import uuid
    app = app_module
    key = "qa-telegram-" + uuid.uuid4().hex
    payload = {"source": "manual_admin", "visual_card_payload": {"pick": {"reason": "qa " * 2200}}}
    first = app.enqueue_telegram_message("manual", "QA ONLY", "Mensaje QA", chat_id="qa", payload=payload, dedupe_key=key)
    assert first["queued"]
    assert json.loads(first["item"]["payload_json"]) == payload
    assert app.enqueue_telegram_message("manual", "QA ONLY", "Mensaje QA", chat_id="qa", dedupe_key=key)["reason"] == "duplicate"
    calls = []
    monkeypatch.setattr(app, "telegram_send_http", lambda *a, **kw: calls.append(1) or app.telegram_delivery_uncertain())
    app.process_premium_telegram_queue(limit=100, force=True)
    row = app.one("SELECT status,attempts FROM telegram_queue WHERE dedupe_key=?", (key,))
    assert row["status"] == "uncertain" and row["attempts"] == 1
    count = len(calls)
    app.process_premium_telegram_queue(limit=100, force=True)
    assert len(calls) == count


def test_free_card_does_not_reveal_premium_metrics(monkeypatch):
    result = cards.build_visual_card_for_message("pick_alert", {"membership": "FREE", "pick": {"odds": 1.85, "reason": "private premium analysis"}})
    assert result["ok"]
    assert "1.85" not in str(result["card"]["metrics"])
    assert "private premium" not in result["card"]["reason"]


def test_explicit_buttons_do_not_expose_admin(app_module):
    markup = app_module.telegram_reply_markup_from_payload({"reply_markup": {"inline_keyboard": [[
        {"text": "Private", "url": "https://example.org/admin/sentinel-issues"},
        {"text": "Picks", "url": "https://example.org/picks"},
    ]]}})
    assert markup == {"inline_keyboard": [[{"text": "Picks", "url": "https://example.org/picks"}]]}


def test_existing_fixture_gallery_is_explicitly_qa(tmp_path):
    from test_telegram_premium_communication_system import SAMPLE_MATCH
    # Reuse the existing fixture; these files are never placed in the delivery queue.
    sample = {**SAMPLE_MATCH, "membership": "PRO"}
    cases = {
        "pick": cards.build_pick_visual_card_payload(sample),
        "combi": cards.build_combi_visual_card_payload({"picks": [sample], "membership": "ELITE"}),
        "result": cards.build_result_visual_card_payload(sample, {}),
        "live": cards.build_live_visual_card_payload(sample),
        "highlight": cards.build_highlight_visual_card_payload(sample, {}),
    }
    assert cases["combi"]["market"] == "1 selección"
    assert cards.build_combi_visual_card_payload({"picks": [sample, sample]})["market"] == "2 selecciones"
    assert cards.build_combi_visual_card_payload({})["market"] == "Sin selecciones publicadas"
    for kind, card in cases.items():
        card["eyebrow"] = "MUESTRA QA · " + card["eyebrow"]
        card["warning"] = "PRUEBA LOCAL · Fixture existente, no un mensaje deportivo real ni una recomendación."
        (tmp_path / f"qa-{kind}.png").write_bytes(cards.build_telegram_visual_card_png(card))


def test_preview_permissions_and_read_only(app_module):
    import os
    visitor = app_module.app.test_client()
    assert visitor.get("/api/admin/telegram/pro-preview").status_code in {401, 403}
    with visitor.session_transaction() as session:
        session["user_role"] = "ELITE"
    assert visitor.get("/api/admin/telegram/pro-preview").status_code == 403
    client = app_module.app.test_client()
    client.get("/local-safe/login/admin", query_string={"token": os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"]})
    connection = app_module.db()
    before = connection.execute("SELECT count(*) FROM telegram_queue").fetchone()[0]
    api = client.get("/api/admin/telegram/pro-preview")
    assert api.status_code == 200
    preview = api.get_json()["preview"]
    assert len(preview["samples"]) == 10
    assert api.get_json()["send_executed"] is False
    assert client.get("/admin/telegram/pro-preview").status_code == 200
    assert connection.execute("SELECT count(*) FROM telegram_queue").fetchone()[0] == before
    connection.close()
    assert "Manchester City" not in json.dumps(preview, ensure_ascii=False)


def test_scope_compiles_and_template_parses(app_module):
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    paths = ["app.py", "engines/telegram_activity_engine.py", "engines/telegram_delivery_engine.py", "engines/telegram_message_formatter.py", "engines/telegram_visual_card_engine.py", "tests/test_telegram_visual_premium.py"]
    for path in paths:
        ast.parse((root / path).read_text(encoding="utf-8-sig"), filename=path)
    app_module.app.jinja_env.parse((root / "templates/admin_telegram_pro_preview.html").read_text(encoding="utf-8"))


def test_real_browser_preview_and_command_center(app_module, tmp_path):
    import os
    import threading
    from pathlib import Path
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server, WSGIRequestHandler

    class Quiet(WSGIRequestHandler):
        def log_request(self, *args, **kwargs):
            pass

    server = make_server("127.0.0.1", 0, app_module.app, threaded=True, request_handler=Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    observations = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=str(Path(os.environ["LOCALAPPDATA"]) / "ms-playwright/chromium-1228/chrome-win64/chrome.exe"), headless=True)
            context = browser.new_context()
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") or route.request.url.startswith("data:") else route.abort())
            context.request.get(base + "/local-safe/login/admin", params={"token": os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"]})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for width in (1366, 390, 430):
                page.set_viewport_size({"width": width, "height": 900})
                response = page.goto(base + "/admin/telegram/pro-preview", wait_until="networkidle")
                assert response.status == 200
                assert page.locator(".telegram-studio article").count() == 10
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                image = page.locator(".telegram-studio img").first
                assert image.evaluate("el => el.complete && el.naturalWidth === 960")
                path = tmp_path / f"telegram-preview-{width}.png"
                page.screenshot(path=str(path), full_page=True)
                page.screenshot(path=str(tmp_path / f"telegram-viewport-{width}.png"))
                page.get_by_text("Caption de la tarjeta", exact=True).first.click()
                assert page.locator(".telegram-studio details").nth(1).get_attribute("open") is not None
                with page.expect_download() as download:
                    page.get_by_text("Descargar PNG", exact=True).first.click()
                download.value.save_as(str(tmp_path / f"telegram-pick-{width}.png"))
                observations.append({"width": width, "http": response.status, "overflow": False, "download": True})
            page.get_by_role("link", name="Centro de mando", exact=True).click()
            assert "/admin/telegram/command-center" in page.url
            page.go_back(wait_until="networkidle")
            assert page.locator("#telegram-title").inner_text() == "Mensajes SHARK"
            assert not errors, errors
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    (tmp_path / "browser-results.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
