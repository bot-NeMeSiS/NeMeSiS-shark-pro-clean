"""Offline structure and ownership checks for reconciling PR60 with PR71.

These supplement, not replace, authenticated Flask and production playback tests.
"""
import ast
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('name',[
 'install_decorative_asset_cache', 'create_client_combi_blueprint',
 'create_client_surfaces_blueprint', 'create_media_review_blueprint',
])
def test_each_existing_and_new_setup_is_called_once(name):
    tree=ast.parse((ROOT/'blueprints/architecture.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==name]
    assert len(calls)==1

@pytest.mark.parametrize('path,signals',[
 ('templates/match_detail.html',['/combinadas?match_id=','Consejos de SHARK sobre este partido','components/highlight_player.html','data-highlight-availability="unavailable"']),
 ('templates/components/v933_ui.html',['Revisar en combinada','/combinadas?pick=','Ver resumen','has_highlight']),
 ('templates/combis.html',['combi-manual-builder','match_catalogue(center.catalogue','components/picks_workspace_nav.html']),
 ('templates/shark.html',['data-shark-question-entry','name="q"','platform-help.css']),
])
def test_current_customer_entries_and_video_are_not_overwritten(path,signals):
    source=(ROOT/path).read_text()
    for text in signals:
        assert text in source
    assert '<<<<<<<' not in source and '>>>>>>>' not in source

@pytest.mark.parametrize('embed,link,expected_button,expected_link',[
    (False,False,False,False), (False,True,False,True), (True,True,True,True),
])
def test_renderer_keeps_link_and_embed_distinct_without_loading_iframe(embed,link,expected_button,expected_link):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape())
    html=str(env.get_template('components/highlight_player.html').module.highlight_player({
      'can_embed':embed,'can_link':link,'decision':'APPROVED' if link else 'REVIEW_REQUIRED',
      'original_url':'https://www.youtube.com/watch?v=officialQA1',
      'embed_url':'https://www.youtube-nocookie.com/embed/officialQA1',
      'title':'SIMULATED_QA <script>not trusted</script>'}))
    assert ('<button' in html)==expected_button
    assert ('<a ' in html)==expected_link
    assert '<iframe' not in html
    assert '<script>not trusted</script>' not in html
