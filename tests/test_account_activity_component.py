"""Pure Jinja autoescape tests over the candidate's real local view model."""
from __future__ import annotations
from datetime import datetime, timezone
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("activity_component_engine", ROOT / "engines/client_activity_engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class _HTML(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.anchors = []
        self.data = []
        self.times = []
        self.listitems = []
        self._anchor = None
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags.append((tag, attrs))
        if tag == "a":
            self._anchor = dict(attrs, text="")
            self.anchors.append(self._anchor)
        if tag == "time":
            self.times.append(attrs)
        if attrs.get("role") == "listitem":
            self.listitems.append(attrs)

    def handle_endtag(self, tag):
        if tag == "a":
            self._anchor = None

    def handle_data(self, text):
        self.data.append(text)
        if self._anchor is not None:
            self._anchor["text"] += text

    @property
    def text(self):
        return " ".join(" ".join(self.data).split())


class AccountActivityComponentTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE user_activity(id TEXT PRIMARY KEY,user_id TEXT,activity_type TEXT,target_type TEXT,target_id TEXT,payload_json TEXT,created_at TEXT);
            CREATE TABLE local_entities(kind TEXT,id TEXT,name TEXT,PRIMARY KEY(kind,id));
            INSERT INTO local_entities VALUES('team','team-1','Norte'),('match','match-1','Norte — Sur'),('competition','league-1','Liga local');
        """)
        self.formatted_times = []
        self.env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
        def display_datetime(value):
            self.formatted_times.append(value)
            # Spy stands in for the app's existing Madrid filter; its own time
            # conversion is covered separately, not certified by this template.
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return "MADRID_LABEL:" + parsed.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")
        self.env.filters["madrid_datetime_label"] = display_datetime
        self.template = self.env.from_string("{% from 'components/account_activity.html' import account_activity_list %}{{ account_activity_list(snapshot, retry_href) }}")

    def tearDown(self):
        self.conn.close()

    def _insert(self, item_id, *, target="team", target_id="team-1", date="2026-10-24T00:00:00Z", payload=None):
        self.conn.execute("INSERT INTO user_activity VALUES(?,?,?,?,?,?,?)", (item_id, "alice", "view", target, target_id, json.dumps(payload or {}), date))

    def _seed(self, count):
        for number in range(count):
            self._insert(f"a{number:03}", date=f"2026-10-24T00:00:{number:02}Z")

    def _resolver(self, target, identifier):
        row = self.conn.execute("SELECT id,name FROM local_entities WHERE kind=? AND id=?", (target, identifier)).fetchone()
        if row is None:
            return {"verified": False, "state": "unknown"}
        return {"verified": True, "target_type": target, "target_id": identifier,
                "canonical_id": row["id"], "name": row["name"]}

    def _snapshot(self, **kwargs):
        return engine.build_client_activity_snapshot(lambda sql, params: self.conn.execute(sql, params).fetchall(),
            user_id="alice", resolve_target=self._resolver, **kwargs)

    def _render(self, snapshot, retry_href="/actividad"):
        rendered = self.template.render(snapshot=snapshot, retry_href=retry_href)
        return rendered, _HTML(rendered)

    def test_counts_and_received_items_7_of_25_20_of_25_5_of_25(self):
        self._seed(25)
        preview = self._snapshot(limit=7)
        first = self._snapshot(limit=20)
        second = self._snapshot(limit=20, cursor=first["next_cursor"])
        for count, snapshot in ((7, preview), (20, first), (5, second)):
            with self.subTest(count=count):
                rendered, parsed = self._render(snapshot)
                self.assertIn(f"Mostrando {count} de 25 acciones guardadas.", parsed.text)
                self.assertEqual(len(parsed.listitems), count)
                self.assertNotIn("20 nuevos", parsed.text)
                self.assertNotIn("Siguiente", parsed.text)
                self.assertNotIn("<style", rendered)
                self.assertTrue(all(attrs.get("class", "").startswith("v933-action") for tag, attrs in parsed.tags if tag == "a"))

    def test_empty_is_distinct_from_read_error_and_does_not_promise_tracking(self):
        rendered, parsed = self._render(self._snapshot())
        self.assertIn('data-client-activity-state="empty"', rendered)
        self.assertIn("No hay acciones guardadas para mostrar.", parsed.text)
        self.assertIn("Abrir pantallas no crea un registro de navegación.", parsed.text)
        self.assertNotIn("No se ha podido", parsed.text)
        self.assertEqual(parsed.anchors[0]["href"], "/calendario")

    def test_error_never_renders_false_zero_and_retry_is_native_get_link(self):
        def broken(*_args):
            raise sqlite3.OperationalError("sensitive local diagnostic")
        snapshot = engine.build_client_activity_snapshot(broken, user_id="alice")
        rendered, parsed = self._render(snapshot)
        self.assertIn('data-client-activity-state="unavailable"', rendered)
        self.assertIn("No se puede confirmar el total", parsed.text)
        self.assertNotIn("Mostrando", parsed.text)
        self.assertNotIn("0", parsed.text)
        self.assertNotIn("No hay acciones guardadas", parsed.text)
        self.assertNotIn("sensitive", rendered)
        retry = parsed.anchors[0]
        self.assertEqual(retry["href"], "/actividad")
        self.assertEqual(retry["text"], "Volver a intentar")
        self.assertFalse(any(tag in {"form", "button", "script"} for tag, _attrs in parsed.tags))

    def test_unknown_dates_are_explicit_without_false_machine_time(self):
        self._insert("undated", date="not-a-date")
        rendered, parsed = self._render(self._snapshot())
        self.assertIn("Fecha no establecida", parsed.text)
        self.assertEqual(parsed.times, [])
        self.assertEqual(self.formatted_times, [])
        self.assertNotIn("Reciente", rendered)

    def test_known_date_has_utc_machine_value_and_existing_filter_for_display(self):
        self._insert("dated", date="2026-10-25T02:10:00+01:00")
        rendered, parsed = self._render(self._snapshot())
        self.assertEqual(parsed.times, [{"datetime": "2026-10-25T01:10:00.000Z"}])
        self.assertEqual(self.formatted_times, ["2026-10-25T01:10:00.000Z"])
        self.assertIn("MADRID_LABEL:", parsed.text)

    def test_autoescape_protects_name_label_and_accessible_link_name(self):
        dangerous = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
        self.conn.execute("UPDATE local_entities SET name=? WHERE kind='team'", (dangerous,))
        self._insert("a")
        snapshot = self._snapshot()
        rendered, parsed = self._render(snapshot)
        self.assertIn("&lt;img", rendered)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("<script", rendered)
        self.assertFalse(any(tag in {"img", "script"} for tag, _attrs in parsed.tags))
        self.assertIn(dangerous, parsed.anchors[0]["aria-label"])
        self.assertFalse(any("onerror" in attrs for _tag, attrs in parsed.tags))

    def test_allowed_engine_destinations_and_payload_urls_never_become_links(self):
        self._insert("team", payload={"href": "javascript:alert(1)", "url": "https://evil.test"})
        self._insert("match", target="match", target_id="match-1")
        self._insert("league", target="competition", target_id="league-1")
        rendered, parsed = self._render(self._snapshot())
        self.assertEqual({item["href"] for item in parsed.anchors}, {"/team/team-1", "/match/match-1", "/competition/league-1"})
        self.assertNotIn("javascript:", rendered)
        self.assertNotIn("evil.test", rendered)

    def test_macro_fails_closed_for_bad_viewmodel_href_and_retry(self):
        self._insert("a")
        for destination in ("javascript:alert(1)", "//evil.test", "/team/other-id", "/team/team-1?next=evil"):
            snapshot = self._snapshot()
            snapshot["items"][0]["href"] = destination
            rendered, parsed = self._render(snapshot)
            self.assertEqual(parsed.anchors, [])
            self.assertNotIn("evil", rendered)
        snapshot = engine.build_client_activity_snapshot(lambda *_args: [], user_id="alice")
        rendered, parsed = self._render(snapshot, retry_href="https://evil.test")
        self.assertEqual(parsed.anchors[0]["href"], "/actividad")
        self.assertNotIn("evil.test", rendered)

    def test_unknown_target_has_no_decorative_detail_button(self):
        self._insert("gone", target_id="deleted-id", payload={"name": "Imagined"})
        rendered, parsed = self._render(self._snapshot())
        self.assertIn("Equipo no disponible.", parsed.text)
        self.assertEqual(parsed.anchors, [])
        self.assertNotIn("Imagined", rendered)

    def test_links_are_keyboard_native_with_accessible_names_and_existing_styles(self):
        self._insert("a")
        rendered, parsed = self._render(self._snapshot())
        link = parsed.anchors[0]
        self.assertEqual(link["text"], "Ver detalle")
        self.assertIn("Norte", link["aria-label"])
        self.assertNotEqual(link.get("tabindex"), "-1")
        self.assertNotIn("onclick", link)
        self.assertTrue(any(attrs.get("role") == "list" and attrs.get("aria-label") for _tag, attrs in parsed.tags))
        self.assertIn("v933-truth-list is-no-icon", rendered)
        source = (ROOT / "templates/components/account_activity.html").read_text(encoding="utf-8")
        self.assertNotIn("|safe", source)

    def test_partial_enrichment_retries_without_hiding_true_count(self):
        self._insert("a")
        def broken_resolver(*_args):
            raise sqlite3.OperationalError("sensitive target error")
        snapshot = engine.build_client_activity_snapshot(lambda sql, params: self.conn.execute(sql, params).fetchall(),
            user_id="alice", resolve_target=broken_resolver)
        rendered, parsed = self._render(snapshot, retry_href="/mi-cuenta")
        self.assertIn("Mostrando 1 de 1 acción guardada.", parsed.text)
        self.assertIn("Algunos detalles no están disponibles.", parsed.text)
        self.assertEqual(parsed.anchors[0]["href"], "/mi-cuenta")
        self.assertNotIn("sensitive", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
