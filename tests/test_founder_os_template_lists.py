"""Founder OS collection rendering. Synthetic data; no database or provider IO."""
from pathlib import Path

import pytest
from jinja2 import DictLoader, Environment, select_autoescape

ROOT = Path(__file__).resolve().parents[1]


def render_founder(snapshot):
    env = Environment(
        loader=DictLoader({
            'base.html': '<main>{% block content %}{% endblock %}</main>',
            'admin_founder_os.html': (ROOT / 'templates/admin_founder_os.html').read_text(encoding='utf-8'),
        }),
        autoescape=select_autoescape(['html']),
    )
    env.filters['madrid_datetime_label'] = str
    return env.get_template('admin_founder_os.html').render(founder_os=snapshot)


def snapshot():
    return {
        'health_state': 'UNKNOWN',
        'alerts': {'items': [], 'counts': {}, 'open': 0},
        'obligations': {'items': [], 'counts': {}, 'known_monthly_cost': 0},
        'providers': {'items': [], 'configured': 0, 'total': 0},
        'sports_data_freshness': {},
        'push': {'configured': False, 'subscriptions': 0},
    }


@pytest.mark.parametrize('bucket', ['alerts', 'providers', 'obligations'])
@pytest.mark.parametrize('variant', ['empty', 'missing', 'null'])
def test_empty_missing_and_null_collections_do_not_iterate_dict_methods(bucket, variant):
    data = snapshot()
    if variant == 'missing':
        data[bucket].pop('items')
    elif variant == 'null':
        data[bucket]['items'] = None
    html = render_founder(data)
    assert 'Control fundador' in html
    assert '0 alertas abiertas en el registro consultado.' in html
    assert 'Todavía no has registrado obligaciones.' in html
    assert html.count('data-founder-install') == 1


def test_all_three_real_collection_keys_render_and_escape_values():
    data = snapshot()
    data['alerts']['items'] = [{'id': 'a1', 'severity': 'HIGH', 'category': 'QA',
        'title': 'Alerta de prueba', 'message': '<script>unsafe</script>', 'status': 'OPEN'}]
    data['providers']['items'] = [{'label': 'Proveedor de prueba', 'configured': False,
        'evidence': {}, 'plan': 'UNKNOWN'}]
    data['obligations']['items'] = [{'id': 'o1', 'label': 'Obligación de prueba',
        'effective_state': 'PENDING', 'amount': 0, 'currency': 'EUR'}]
    html = render_founder(data)
    assert 'Alerta de prueba' in html
    assert 'Proveedor de prueba' in html
    assert 'Obligación de prueba' in html
    assert '0.00 EUR' in html
    assert '&lt;script&gt;unsafe&lt;/script&gt;' in html
    assert '<script>unsafe</script>' not in html
    assert '/admin/founder-os/alerts/a1/ack' in html
    assert '/admin/founder-os/obligations/o1/paid' in html
    assert '0 alertas abiertas en el registro consultado.' not in html


def test_inbox_preserves_twenty_item_limit():
    data = snapshot()
    data['alerts']['items'] = [{'id': str(i), 'severity': 'LOW', 'category': 'QA',
        'title': f'Unique alert {i:03d}', 'message': 'Synthetic', 'status': 'ACK'} for i in range(30)]
    html = render_founder(data)
    assert 'Unique alert 019' in html
    assert 'Unique alert 020' not in html
    assert html.count('class="founder-os-alert severity-low"') == 20


def test_integrations_center_renders_contribution_evidence_and_management_link():
    data=snapshot()
    data['providers'].update({'with_evidence':1,'attention':0,'billing_tracked':1,
        'evidence_policy':'Solo evidencia persistida/local; abrir Founder OS no llama a proveedores externos.'})
    data['providers']['items']=[{
        'label':'The Odds API','category':'Datos / cuotas','criticality':'CRITICAL',
        'configured':True,'enabled':True,'operational_state':'CACHE_REUSED',
        'plan':'PAID','billing_state':'TRACKED','contribution':'Aporta cuotas 1X2 reales.',
        'admin_url':'/admin/matches-sync','evidence':{'requests_remaining':123,'external_calls':0,'error_present':False}
    }]
    html=render_founder(data)
    assert 'Centro de integraciones' in html
    assert 'Aporta cuotas 1X2 reales.' in html
    assert 'Créditos restantes' in html and '>123<' in html
    assert '/admin/matches-sync' in html
    assert 'abrir Founder OS no llama a proveedores externos' in html
