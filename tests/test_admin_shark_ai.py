"""SHARK Admin's pure intent boundary and mocked-provider resilience."""
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from engines.admin_control_engine import AdminControlStore
from engines.shark_ai_product_assistant_engine import admin_intent, admin_deterministic_answer, admin_openai_answer
from blueprints.admin_master_control import settings_values, master_snapshot


class Response:
    def __init__(self, value):
        self.data = value if isinstance(value, bytes) else json.dumps(value).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, length):
        return self.data[:length]


def output(text):
    return {"output":[{"type":"message","content":[{"type":"output_text","text":text}]}]}


SNAPSHOT = {"facts":[{"label":"Usuarios","value":4},{"label":"Partidos hoy","value":None}],
            "areas":[{"key":"sports","state":"SIN DATOS"}],"recommendations":[]}


@pytest.mark.parametrize("message,action,params", [
    ("Desactiva temporalmente highlights", "settings.update", {"key":"highlights_enabled","value":False}),
    ("Activa highlights", "settings.update", {"key":"highlights_enabled","value":True}),
    ("Activa el banner", "settings.update", {"key":"banner_enabled","value":True}),
    ("Desactiva el banner", "settings.update", {"key":"banner_enabled","value":False}),
    ("Pon este aviso: Actualizaci\u00f3n prevista", "settings.update", {"key":"banner_text","value":"Actualizaci\u00f3n prevista"}),
    ("Sincroniza los partidos", "sports.sync", {}),
    ("Comprueba Telegram", "telegram.dry_run", {}),
    ("Reintenta los Telegram fallidos", "telegram.retry_failed", {}),
    ("Ejecuta Sentinel", "sentinel.scan", {}),
])
def test_known_intents_only_return_registered_proposals(message,action,params):
    assert admin_intent(message) == {"action_id":action,"parameters":params}


@pytest.mark.parametrize("message", [None,"", "x"*1201,"OPENAI_API_KEY=privatevalue", "Ejecuta shell", "Haz deploy", "borra la base", "haz un pago real"])
def test_unsafe_or_invalid_intents_are_blocked(message):
    result=admin_intent(message)
    assert result["kind"] == "BLOCKED" and "action_id" not in result


@pytest.mark.parametrize("message", ["No desactiva highlights", "\u00bfPor qu\u00e9 no aparecen partidos?", "Qu\u00e9 significa activa highlights", "Observa el sistema"])
def test_questions_negations_and_unknowns_do_not_propose_writes(message):
    result=admin_intent(message)
    assert result["kind"] == "INFORMATION" and "action_id" not in result


def test_ambiguous_followup_never_reuses_action_authority():
    result=admin_intent("Eso que acabamos de ver, arr\u00e9glalo", previous={"action_id":"sports.sync"})
    assert result["kind"] == "CLARIFICATION" and "action_id" not in result


def test_code_request_is_pending_sentinel_improvement_not_code_execution():
    message="Prepara mejora para la pantalla Live"
    result=admin_intent(message)
    assert result["action_id"] == "sentinel.create_improvement"
    assert result["parameters"]["route"] == "/live" and result["parameters"]["detail"] == message


def test_deterministic_answer_preserves_unknowns_and_does_not_invent_cause():
    answer=admin_deterministic_answer("Por qu\u00e9 no aparecen partidos",SNAPSHOT)
    assert "DATOS INSUFICIENTES" in answer["message"]
    assert answer["facts"][1]["value"] is None
    assert answer["source"] == "DETERMINISTIC" and answer["executed"] is False


@pytest.mark.parametrize("key,model", [("","gpt-model"),("local-test-key",""),(None,"gpt-model"),("local-test-key","../../evil")])
def test_missing_or_invalid_provider_config_never_calls_transport(key,model):
    def forbidden(*args,**kwargs):
        pytest.fail("Provider must not be called")
    assert admin_openai_answer("Estado",SNAPSHOT,api_key=key,model=model,opener=forbidden) is None


@pytest.mark.parametrize("message", ["token=privatevalue", "Bearer privatevalue", "Sincroniza partidos", "Hazlo", "x"*1201])
def test_transport_revalidates_prompt_and_refuses_operational_commands(message):
    def forbidden(*args,**kwargs):
        pytest.fail("Provider must not be called")
    assert admin_openai_answer(message,SNAPSHOT,api_key="local-test-key",model="test-model",opener=forbidden) is None


def test_provider_input_is_only_known_numeric_facts_and_enum_states():
    captured=[]
    poisoned={"facts":[{"label":"Usuarios","value":4},{"label":"EXTERNAL_PRIVATE", "value":1},
        {"label":"PRO","value":"PRIVATE"},{"label":"ELITE","value":True}, {"label":"Partidos hoy","value":None}],
        "areas":[{"key":"sports","state":"SIN DATOS","detail":"PRIVATE"},
        {"key":"PRIVATE","state":"OK"},{"key":"db","state":"PRIVATE"}],
        "settings":{"password":"PRIVATE"}, "users":[{"cookie":"PRIVATE"}], "audit":[{"session_id":"PRIVATE"}]}
    def opener(req,timeout):
        payload=json.loads(req.data)
        captured.append(payload)
        assert req.full_url == "https://api.openai.com/v1/responses" and timeout == 12
        assert req.headers["Authorization"] == "Bearer local-test-key"
        assert "PRIVATE" not in req.data.decode() and "local-test-key" not in req.data.decode()
        assert payload["store"] is False and "tools" not in payload
        data=json.loads(payload["input"])
        assert data["context"]["facts"] == [{"label":"Usuarios","value":4},{"label":"Partidos hoy","value":None}]
        assert data["context"]["areas"] == [{"key":"sports","state":"SIN DATOS"}]
        return Response(output("DATOS INSUFICIENTES: falta evidencia de disponibilidad externa."))
    assert admin_openai_answer("Estado",poisoned,api_key="local-test-key",model="test-model",opener=opener).startswith("DATOS INSUFICIENTES")
    assert len(captured) == 1


@pytest.mark.parametrize("raw", [b'{broken',b'x'*70000,[],{"output":"bad"},{"output":[None]}, {"output":[{"type":"function_call","name":"shell","arguments":"execute"}]}], ids=["json","oversized","list","output_type","null_item","tool_call"])
def test_invalid_or_tool_provider_output_falls_back(raw):
    assert admin_openai_answer("Estado",SNAPSHOT,api_key="local-test-key",model="test-model",opener=lambda *a,**kw:Response(raw)) is None


@pytest.mark.parametrize("text", ["OPENAI_API_KEY=privatevalue", "local-test-key", "He enviado Telegram", "Hemos aplicado los cambios", "deploy completado"])
def test_sensitive_or_false_execution_claims_fall_back(text):
    assert admin_openai_answer("Estado",SNAPSHOT,api_key="local-test-key",model="test-model",opener=lambda *a,**kw:Response(output(text))) is None


def test_provider_failure_does_not_break_deterministic_diagnosis():
    def failing(*args,**kwargs):
        raise TimeoutError("PRIVATE_EXCEPTION")
    assert admin_openai_answer("Estado",SNAPSHOT,api_key="local-test-key",model="test-model",opener=failing) is None
    answer=admin_deterministic_answer("Estado",SNAPSHOT)
    assert answer["source"] == "DETERMINISTIC" and "PRIVATE_EXCEPTION" not in json.dumps(answer)


def test_model_action_json_is_only_text_and_never_dispatched():
    text='{"action_id":"sports.sync","confirmation":true}'
    answer=admin_openai_answer("Estado",SNAPSHOT,api_key="local-test-key",model="test-model",opener=lambda *a,**kw:Response(output(text)))
    assert answer == text and type(answer) is str


def test_corrupt_settings_fail_closed_without_breaking_rendering(tmp_path):
    store=AdminControlStore(tmp_path/"test.sqlite","V941_TEST");store.initialize()
    with sqlite3.connect(store.path) as conn:
        conn.execute("INSERT INTO automation_state VALUES('admin_control.settings.highlights_enabled','bad-json','now')")
    a=SimpleNamespace(DB_PATH=str(store.path),APP_VERSION="V941_TEST")
    assert settings_values(a) == {"highlights_enabled":False,"banner_enabled":False,"banner_text":""}


def test_snapshot_drops_untrusted_provider_labels_timestamps_and_strings(tmp_path):
    store=AdminControlStore(tmp_path/"test.sqlite","V941_TEST");store.initialize()
    (tmp_path/"VERSION.txt").write_text("V941_TEST")
    a=SimpleNamespace(DB_PATH=str(store.path),APP_VERSION="V941_TEST",BASE_DIR=tmp_path,
        get_public_home_sports_summary=lambda:{"storage_status":"ok","valid_matches_today_count":0,"valid_live_events":[]},
        v945_provider_health_snapshot=lambda:{"providers":[{"key":"sportsdb","label":"PRIVATE",
            "configured":True,"status":"PRIVATE","status_label":"PRIVATE","observed_at":"PRIVATE","processed":"PRIVATE"}],"job_finished_at":"PRIVATE"},
        v928_telegram_overview_fast=lambda:{"last_sent_at":"PRIVATE"},v928_automation_overview_fast=lambda:{},
        env_present=lambda name:False,now_iso=lambda:"2026-09-23T12:00:00+02:00")
    snap=master_snapshot(a)
    assert "PRIVATE" not in json.dumps(snap)
    assert snap["providers"][0]["label"] == "TheSportsDB"
    assert snap["job_last_cycle"] is None and snap["telegram"]["last_sent_at"] is None
    assert snap["settings_readable"] is True and snap["external_calls"] == 0
def test_preview_links_cannot_leave_simulated_context():
    from blueprints.admin_master_control import _preview_links
    from html.parser import HTMLParser
    html='<a href="/picks" target="_top">Picks</a><a href="/api/payments/checkout">Pay</a><a href="https://example.com">Remote</a><a href="/admin/client-preview?page=live&amp;plan=ELITE">Live</a>'
    class Links(HTMLParser):
        def __init__(self): super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            if tag=='a':self.links.append(dict(attrs))
    parsed=Links();parsed.feed(_preview_links(html,'FREE'))
    assert parsed.links[0]['href']=='/admin/client-preview?page=picks&plan=FREE&viewport=390'
    assert 'target' not in parsed.links[0]
    assert 'href' not in parsed.links[1] and 'href' not in parsed.links[2]
    assert parsed.links[3]['href']=='/admin/client-preview?page=live&plan=FREE&viewport=390'

def test_opaque_personal_or_credential_text_never_reaches_provider():
    canary='OpaqueCanaryAlphanumeric987654321'
    def opener(req,**kwargs):
        body=json.loads(req.data)
        assert canary not in req.data.decode()
        assert 'personal@example.com' not in req.data.decode()
        inner=json.loads(body['input'])
        assert inner['topic']=='general'
        return Response(output('DATOS INSUFICIENTES'))
    assert admin_openai_answer('Estado '+canary+' personal@example.com',SNAPSHOT,api_key='local-test-key',model='test-model',opener=opener)=='DATOS INSUFICIENTES'


def reliability_snapshot_for_questions():
    return {
        "facts": [],
        "recommendations": [],
        "runtime": {"app_version":"V941_TEST","version_file":"V941_TEST","commit":None},
        "reliability": {
            "state":"ATENCIÓN","memory_available":True,
            "issues":[
                {"id":"SENT-2026-AABBCCDD","status":"FIXED_PENDING_VERIFICATION","seen_count":2,"title":"QA recurrente","route":"/live","component":"sports","verification_record":None},
                {"id":"SENT-2026-11223344","status":"RESOLVED","seen_count":1,"title":"QA resuelta","verification_record":{"result":"PASS"}},
            ],
            "timeline":[{"issue_id":"SENT-2026-AABBCCDD","event":"VERIFICATION_FAILED","result":"FAIL","at_madrid":"2026-09-25T20:00:00+02:00"}],
            "radar":{
                "alerts":[{"state":"RIESGO ALTO","evidence":"Sync retrasada","reason":"Supera el umbral","impact":"Calendario puede quedar antiguo","href":"/admin/data-center"}],
                "drift":{"state":"UNKNOWN","main_sha":"a"*40,"candidate_sha":"b"*40,"deployed_sha":None,"render_sha":None,"mismatches":[]}
            }
        }
    }


@pytest.mark.parametrize("question,expected",[
    ("¿Qué está mal?","DIAGNÓSTICO"),
    ("¿Qué riesgo tenemos?","RIESGO"),
    ("¿Qué falló recientemente?","último fallo"),
    ("¿Qué está sin verificar?","requieren verificación"),
    ("¿Producción está alineada?","SHA desplegado no confirmado"),
    ("¿Qué debería vigilar?","Sync retrasada"),
    ("¿Cómo está NeMeSiS?","estado de fiabilidad"),
])
def test_admin_reliability_questions_have_specific_local_answers(question,expected):
    answer=admin_deterministic_answer(question,reliability_snapshot_for_questions())
    assert expected.casefold() in answer["message"].casefold()
    assert answer["source"]=="DETERMINISTIC" and answer["local_only"] is True and answer["executed"] is False
