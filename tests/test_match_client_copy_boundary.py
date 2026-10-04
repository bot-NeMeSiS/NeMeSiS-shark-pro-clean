import pytest

@pytest.mark.parametrize('path,technical', [('/match/real-cache-record',False),('/admin/matches',True)])
def test_match_diagnostics_follow_the_surface(app_module,path,technical):
 template=app_module.app.jinja_env.from_string('''
 {% from 'components/v933_ui.html' import data_provenance_badge with context %}
 {% from 'components/v944_match_center.html' import transparency_meta with context %}
 {{ data_provenance_badge('INTERNAL_PROVIDER_DIAGNOSTIC','2026-10-04') }}
 {{ transparency_meta({'transparency':{'score':{'evidence':'INTERNAL_EVIDENCE_DIAGNOSTIC'}}},'score') }}
 ''')
 with app_module.app.test_request_context(path):html=template.render()
 assert ('INTERNAL_EVIDENCE_DIAGNOSTIC' in html) is technical
 assert ('v935-provenance' in html) is technical

@pytest.mark.parametrize('message',['provider unavailable','cron FAIL','runtime PARTIAL','storage DB_PATH'])
def test_match_component_errors_use_client_language(app_module,message):
 template=app_module.app.jinja_env.from_string("{% from 'components/v944_match_center.html' import state_notice with context %}{{ state_notice(component) }}")
 with app_module.app.test_request_context('/match/real-cache-record'):
  html=template.render(component={'state':'error','message':message})
 assert message not in html
 assert 'No disponible todavía.' in html

@pytest.mark.parametrize('code,label',[('NO_STATISTICS','Estadísticas todavía no disponibles.'),('NO_LINEUPS','Alineaciones todavía no disponibles.'),('PROVIDER_UNAVAILABLE','Datos temporalmente limitados.')])
def test_known_technical_states_have_useful_customer_copy(app_module,code,label):
 template=app_module.app.jinja_env.from_string("{% from 'components/v933_ui.html' import client_message with context %}{{ client_message(code) }}")
 with app_module.app.test_request_context('/match/real-cache-record'):html=template.render(code=code)
 assert label in html
 assert code not in html
