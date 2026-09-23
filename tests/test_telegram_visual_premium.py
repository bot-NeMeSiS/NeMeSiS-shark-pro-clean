"""Presentation and transport contracts. Transport is always intercepted locally."""
from datetime import datetime, timedelta, timezone
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


def test_queue_payload_is_bounded_structured_json(app_module):
    import uuid
    app = app_module
    payload = {
        "source": "manual_admin",
        "membership": "ELITE",
        "visual_card_type": "pick_alert",
        "visual_card_enabled": True,
        "visual_card_payload": {
            "pick": {
                "home_team": "QA Norte",
                "away_team": "QA Sur",
                "selection": "QA solamente",
                "reason": "x" * 200000,
            }
        },
    }
    encoded = app.serialize_telegram_queue_payload(payload)
    decoded = json.loads(encoded)
    assert len(encoded.encode("utf-8")) <= app.TELEGRAM_QUEUE_PAYLOAD_MAX_BYTES
    assert decoded["_queue_payload_truncated"] is True
    assert decoded["source"] == "manual_admin"
    assert decoded["visual_card_type"] == "pick_alert"
    assert decoded["visual_card_payload"]["pick"]["home_team"] == "QA Norte"
    key = "qa-telegram-bounded-" + uuid.uuid4().hex
    queued = app.enqueue_telegram_message("manual", "QA ONLY", "Mensaje QA", chat_id="qa", payload=payload, dedupe_key=key)
    stored = queued["item"]["payload_json"]
    assert len(stored.encode("utf-8")) <= app.TELEGRAM_QUEUE_PAYLOAD_MAX_BYTES
    assert json.loads(stored)["_queue_payload_truncated"] is True

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


@pytest.mark.parametrize("bad", [None, "null", "undefined", "N/A", {"private": "object"}, ["raw"], float("nan")])
def test_optional_fields_do_not_leak_objects_or_technical_markers(bad):
    item = {key: bad for key in ("home_team", "away_team", "competition_name", "selection", "reason", "risk", "stake", "confidence", "value")}
    text = fmt.format_pick_message(item)
    assert all(marker not in text for marker in ("None", "null", "undefined", "N/A", "private", "raw", "nan"))


def test_free_never_hides_available_risk():
    from engines.telegram_intelligence_engine import build_premium_message
    pick = {"risk_level": "Alto", "warning": "Rotación pendiente de confirmar"}
    assert "Rotación pendiente de confirmar" in fmt.format_membership_pick_message(pick, membership="FREE")
    result = cards.build_visual_card_for_message("pick_alert", {"membership": "FREE", "pick": pick})
    assert result["card"]["warning"] == pick["warning"]
    assert ("Riesgo", "Alto") in result["card"]["metrics"]
    assert "Rotación pendiente de confirmar" in build_premium_message(pick, "FREE")["preview"]


@pytest.mark.parametrize("rights", [None, "REVIEW_REQUIRED", "UNKNOWN_RIGHTS", "BLOCKED"])
def test_pending_highlight_rights_are_not_sent(rights):
    highlight = {"url": "https://example.invalid/video", "rights_status": rights, "commercial_use_status": "ALLOWED"}
    assert not fmt.highlight_link(highlight)
    assert "https://" not in fmt.format_highlight_message({}, highlight)
    assert not should_send_highlight_alert({}, highlight)


def test_highlight_requires_channel_and_attribution():
    approved = {"url": "https://example.invalid/video", "rights_status": "ATTRIBUTION_REQUIRED", "commercial_use_status": "ALLOWED", "allowed_channels": ["TELEGRAM"], "attribution": "Canal de pruebas SIMULATED_QA"}
    assert fmt.highlight_link(approved) == approved["url"]
    assert approved["attribution"] in fmt.format_highlight_message({}, approved)
    assert not fmt.highlight_link({**approved, "attribution": ""})
    assert not fmt.highlight_link({**approved, "allowed_channels": ["APP"]})


def test_stale_live_never_presents_stale_score_or_stats():
    match = {"status": "live", "live_updated_at": "2020-01-01T12:00:00Z", "score": "4-3", "minute": 89, "corners": 8}
    text = fmt.format_live_alert_message(match)
    assert "4–3" not in text and "córners 8" not in text and "89" not in text
    assert cards.build_live_visual_card_payload(match)["center"] == "Marcador pendiente"


@pytest.mark.parametrize("result,label", [("won", "ACERTADO"), ("lost", "FALLADO"), ("void", "NULO"), ("pending", "PENDIENTE")])
def test_result_grading_and_historical_quote(result, label):
    pick = {"result_status": result, "selection": "Local", "odds": 1.87}
    match = {"status": "FT", "score": "2-1"}
    text = fmt.format_result_message(match, pick)
    assert label in text and "1.87" in text
    assert cards.build_result_visual_card_payload(match, pick)["market"] == label


def test_exact_cached_logo_reused_read_only(tmp_path, monkeypatch):
    import sqlite3
    from PIL import Image
    monkeypatch.setattr(cards, "STATIC_ROOT", tmp_path)
    Image.new("RGBA", (80, 50), (65, 170, 190, 255)).save(tmp_path / "simulated.png")
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE team_logo_cache(logo_url TEXT,local_path TEXT,is_fallback INTEGER)")
    conn.execute("INSERT INTO team_logo_cache VALUES(?,?,0)", ("https://allowed.invalid/crest.png", "/static/simulated.png"))
    conn.execute("PRAGMA query_only=ON")
    source = {"pick": {"home_logo": "https://allowed.invalid/crest.png", "away_logo": "https://other.invalid/crest.png"}}
    before = conn.total_changes
    result = cards.resolve_cached_visual_payload(source, conn)
    assert conn.total_changes == before
    assert result["pick"]["home_logo"] == "/static/simulated.png"
    assert result["pick"]["away_logo"] == source["pick"]["away_logo"]
    assert source["pick"]["home_logo"].startswith("https:")
    conn.close()


@pytest.mark.parametrize("logos", [2, 1, 0, -1])
def test_crest_population_and_competition_logo(tmp_path, monkeypatch, logos):
    from PIL import Image
    monkeypatch.setattr(cards, "STATIC_ROOT", tmp_path)
    Image.new("RGBA", (150, 45), (65, 170, 190, 255)).save(tmp_path / "simulated.png")
    (tmp_path / "broken.png").write_bytes(b"SIMULATED_QA invalid image")
    item = {"home_logo": "/static/simulated.png" if logos > 0 else None,
            "away_logo": "/static/simulated.png" if logos > 1 else "/static/broken.png" if logos < 0 else None,
            "competition_logo": "/static/simulated.png"}
    card = cards.build_visual_card_for_message("pick_alert", item)
    assert card["ok"]
    assets = card["asset_diagnostics"]
    assert assets["competition"] == "local_crest"
    assert (assets["left"] == "local_crest") == (logos > 0)
    assert (assets["right"] == "local_crest") == (logos > 1)


@pytest.mark.parametrize("error,uncertain", [(400, False), (500, True)])
def test_button_rejection_retry_or_uncertainty(transport, monkeypatch, error, uncertain):
    app, calls = transport
    def send(url, data):
        calls.append(data.copy())
        if len(calls) == 1:
            raise urllib.error.HTTPError("https://example.invalid/redacted", error, "Bad Request", {}, io.BytesIO(b'{"ok":false,"description":"BUTTON_URL_INVALID secret-do-not-log"}'))
        return {"ok": True, "sent": True}
    monkeypatch.setattr(app, "telegram_post_send_message", send)
    result = app.telegram_send_http("qa", "Mensaje", payload={"app_url": "https://example.invalid/picks"})
    assert bool(result.get("delivery_uncertain")) == uncertain
    assert len(calls) == (1 if uncertain else 2)
    if not uncertain:
        assert "reply_markup" not in calls[1] and result["sent"]
    assert "secret-do-not-log" not in str(result)


def test_preview_recovers_actual_nested_delivery_evidence(app_module):
    app = app_module
    delivery_id = app.log_telegram_delivery("qa", "pick_alert", "SIMULATED_QA", "SENT", {
        "sent": True, "source": "manual_admin", "dedupe_key": "qa-visual-only",
        "sent_at_madrid": "2026-09-23T21:00:00+02:00", "visual_card": {"mode": "text_fallback", "reason": "visual_render_failed"}})
    with app.app.test_request_context("/admin/telegram/pro-preview"):
        result = app.v810_telegram_preview_samples()
    evidence = next(item for item in result["delivery_evidence"] if item["id"] == delivery_id)
    assert evidence["visual"] == "Fallback de texto"
    assert evidence["source"] == "manual_admin" and evidence["dedupe"]
    assert evidence["reason"] == "visual_render_failed"


def test_simulated_qa_representative_gallery(tmp_path, monkeypatch):
    from PIL import Image, ImageDraw
    from time import perf_counter
    from decimal import Decimal
    monkeypatch.setattr(cards, "STATIC_ROOT", tmp_path)
    for name, color in (("home", "#49b4d0"), ("away", "#e6ba64"), ("league", "#d7e8f0")):
        badge = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        draw.rounded_rectangle((4, 4, 96, 96), 8, fill=color)
        draw.text((22, 34), "QA", font=cards._card_font(32, True), fill="#09151f")
        badge.save(tmp_path / (name + ".png"))
    match = {"home_team": "Atlético QA Norte", "away_team": "Unión QA Sur", "competition_name": "Liga de pruebas · SIMULATED_QA",
             "home_logo": "/static/home.png", "away_logo": "/static/away.png", "competition_logo": "/static/league.png",
             "kickoff_iso": "2026-09-24T19:00:00Z", "status": "scheduled", "market": "Doble oportunidad", "selection": "Local o empate · 1X",
             "odds": 1.78, "stake_units": 1, "confidence": "Media", "risk_level": "Moderado", "membership": "PRO",
             "reason": "Contexto sintético para evaluar legibilidad. No es una recomendación real.", "warning": "SIMULATED_QA · Sin envío ni apuesta real."}
    legs = [match, {**match, "home_team": "Deportivo QA Este", "away_team": "Club QA Oeste", "odds": 1.62}, {**match, "home_team": "Norte QA", "away_team": "Sur QA", "odds": 1.5}]
    combi = {"picks": legs, "membership": "ELITE", "total_odds": str(Decimal('1.78') * Decimal('1.62') * Decimal('1.5')), "stake_units": 0.5, "risk_level": "Alto", "reason": "Tres selecciones sintéticas. Cada selección añade riesgo.", "title": "Combinada de pruebas"}
    now = datetime.now(timezone.utc)
    live = {**match, "kickoff_iso": (now - timedelta(minutes=63)).isoformat(), "status": "LIVE", "live_updated_at": now.isoformat(), "home_score": 1, "away_score": 0, "minute": 63, "event_title": "Gol local · evento sintético"}
    final = {**match, "kickoff_iso": (now - timedelta(hours=3)).isoformat(), "status": "FT", "home_score": 2, "away_score": 1}
    highlight = {"url": "https://example.invalid/resumen-qa", "rights_status": "OWNED", "commercial_use_status": "ALLOWED", "allowed_channels": ["TELEGRAM"]}
    cases = {"pick": cards.build_pick_visual_card_payload(match), "combi": cards.build_combi_visual_card_payload(combi),
             "live": cards.build_live_visual_card_payload(live), "result": cards.build_result_visual_card_payload(final, {**match, "result_status": "won"}),
             "highlight": cards.build_highlight_visual_card_payload(final, highlight)}
    copy = {"pick": fmt.format_pick_message(match), "combi": fmt.format_combi_message(combi), "live": fmt.format_live_alert_message(live),
            "result": fmt.format_result_message(final, {**match, "result_status": "won"}), "highlight": fmt.format_highlight_message(final, highlight)}
    assert "63" in copy["live"] and "1–0" in copy["live"] and "EN DIRECTO" in copy["live"]
    assert Decimal("4.3254") == Decimal(combi["total_odds"])
    measurements = []
    for kind, card in cases.items():
        card["eyebrow"] = "SIMULATED_QA · " + card["eyebrow"]
        card["warning"] = "SIMULATED_QA · Datos y símbolos de prueba. No enviado."
        t0 = perf_counter()
        png = cards.build_telegram_visual_card_png(card)
        measurements.append({"kind": kind, "ms": round((perf_counter() - t0) * 1000, 2), "bytes": len(png)})
        (tmp_path / f"simulated-{kind}.png").write_bytes(png)
        (tmp_path / f"simulated-{kind}.txt").write_text("SIMULATED_QA\n" + copy[kind], encoding="utf-8")
    for count in (2, 3):
        card = cards.build_combi_visual_card_payload({**combi, "picks": legs[:count]})
        assert card["market"] == f"{count} selecciones"
    long = {**match, "home_team": "Asociación Deportiva QA de Peñíscola y San Sebastián", "away_team": "Q" * 180, "competition_name": "Campeonato de fútbol sintético extraordinariamente largo " * 3, "odds": None, "home_logo": None, "away_logo": None}
    long_card = cards.build_pick_visual_card_payload(long)
    long_card["eyebrow"] = "SIMULATED_QA · NOMBRES LARGOS"
    (tmp_path / "simulated-long.png").write_bytes(cards.build_telegram_visual_card_png(long_card))
    for width, height in ((480, 500), (640, 900), (960, 1000)):
        png = cards.build_telegram_visual_card_png(long_card, width, height)
        with Image.open(io.BytesIO(png)) as image:
            assert image.width <= width and image.height <= max(height, 540)
    (tmp_path / "render-cost.json").write_text(json.dumps(measurements, indent=2), encoding="utf-8")


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
            browser_path = os.environ.get("NEMESIS_QA_CHROMIUM") or pw.chromium.executable_path
            browser = pw.chromium.launch(executable_path=browser_path, headless=True)
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
