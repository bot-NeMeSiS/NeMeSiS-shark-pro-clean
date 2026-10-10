"""Temporary branch-only refinements identified by isolated browser QA."""
from pathlib import Path

path = Path('tests/test_home_league_delivery.py')
text = path.read_text()
old = "broken.scroll_into_view_if_needed();broken.evaluate('(el)=>el.loading=\"eager\"')"
new = "broken.locator('..').scroll_into_view_if_needed();broken.evaluate('(el)=>el.loading=\"eager\"')"
assert old in text
text = text.replace(old, new)
text = text.replace("@pytest.mark.parametrize('javascript',[True,False])", "@pytest.mark.parametrize('javascript',[True,False])\n@pytest.mark.parametrize('public',[False,True])")
text = text.replace('browser, app_module, width, javascript):', 'browser, app_module, width, javascript, public):')
text = text.replace('markup = markup_for(app_module)\n', "markup = markup_for(app_module, public=public)\n    page_path = '/' if public else '/app'\n")
text = text.replace("if url.path == '/app': route.fulfill", 'if url.path == page_path: route.fulfill')
text = text.replace("page.goto('https://league-home.invalid/app')", "page.goto('https://league-home.invalid'+page_path)")
text = text.replace("agenda=page.locator('[data-home-league-agenda=\"today\"]')", "agenda=page.locator('[data-home-league-agenda=\"'+('public-today' if public else 'today')+'\"]')")
text = text.replace("f'home-client-{width}", "f'home-{\"public\" if public else \"client\"}-{width}")
text = text.replace("assert page.locator('.home-agenda-focus details').count() == 0", "assert agenda.locator('details').count() == 0")
path.write_text(text)
path = Path('static/design-system.css')
text = path.read_text()
old = '@media(max-width:760px) {\n  .home-agenda-matches'
new = '@media(max-width:760px) {\n  .home-league-index { flex-wrap: nowrap; overflow-x: auto; max-width: 100%; padding-block: 3px 8px; scrollbar-width: thin; }\n  .home-league-index a { flex: 0 0 auto; max-width: 85vw; }\n  .home-agenda-matches'
assert old in text
path.write_text(text.replace(old,new))
