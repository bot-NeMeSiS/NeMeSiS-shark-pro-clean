import importlib.util
from engines.automation_domains import DOMAINS


def test_production_domain_adapters_resolve_and_routes_exist(app_module):
    routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    for domain in DOMAINS:
        for module in domain['modules']:
            assert importlib.util.find_spec(module) is not None, module
        assert domain['endpoint'] in routes
        assert domain['diagnostic'].split('#')[0] in routes
    assert len(DOMAINS) == 6
