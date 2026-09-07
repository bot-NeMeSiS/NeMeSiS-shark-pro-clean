import pytest
from html.parser import HTMLParser
from jinja2 import ChoiceLoader, DictLoader


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.nodes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


@pytest.mark.parametrize('saved', [False, True])
def test_favorites_help_does_not_replace_existing_sports_content(app_module, saved):
    env=app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader,
    ]))
    data={'favorite_insights':{'by_kind':{'team':[{'name':'QA'}] if saved else [],'league':[],'match':[]}},
          'favorite_feed':[],'favorite_bundle':{'live':[],'picks':[]},'favorites':[]}
    with app_module.app.test_request_context('/favorites'):
        html=env.get_template('favorites.html').render(data=data)
    nodes=Elements(html).nodes
    help_node=next(attrs for tag,attrs in nodes if tag=='details' and attrs.get('class')=='ns-favorites-help')
    assert ('open' in help_node) is not saved
    assert html.index('</details>') < html.index('Partidos relacionados')
    assert any(tag=='form' and attrs.get('action')=='/favorites' and attrs.get('method')=='post' for tag,attrs in nodes)
    assert 'Crea tu primer favorito' not in html


def test_access_form_preserves_destination_and_fields(app_module):
    env=app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader,
    ]))
    with app_module.app.test_request_context('/cliente-login?next=/favorites'):
        html=env.get_template('client_login.html').render(data={})
    nodes=Elements(html).nodes
    form=next(attrs for tag,attrs in nodes if tag=='form')
    assert form['action']=='/cliente-login' and form['method']=='post'
    inputs=[attrs for tag,attrs in nodes if tag=='input']
    assert {n.get('name') for n in inputs} >= {'login','password','next','plan'}
    assert next(n for n in inputs if n.get('name')=='next')['value']=='/favorites'
