import pytest
from playwright.sync_api import sync_playwright
from tools.run_autonomous_product_qa import inspect_text_geometry


def test_text_geometry_detects_overlap_and_accepts_separate_lines():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width":390,"height":844})
        page.set_content('<div class="v944-match-header__status"><span>Final</span><section class="v944-score-widget"><strong>2-0</strong></section><time>Domingo, 30 de agosto - 21:00</time></div>')
        assert inspect_text_geometry(page)["match_text_status"] == "PASS"
        circle = page.add_style_tag(content=".v944-match-header__status{border:1px solid cyan;border-radius:999px}")
        assert inspect_text_geometry(page)["match_text_status"] == "FAIL"
        circle.evaluate("node=>node.remove()")
        page.add_style_tag(content=".v944-score-widget,time{position:absolute;top:40px;left:20px}")
        assert inspect_text_geometry(page)["match_text_status"] == "FAIL"
        page.set_content("<main><h1>Mercado de datos</h1></main><nav class='v933-admin-mobile-nav'>Panel</nav>")
        page.add_style_tag(content="nav{position:fixed;inset:0 0 auto;height:90px}")
        assert inspect_text_geometry(page)["heading_status"] == "FAIL"
        page.add_style_tag(content="main{padding-top:100px}")
        assert inspect_text_geometry(page)["heading_status"] == "PASS"
        page.set_content("<main>Sin cabecera en esta superficie</main>")
        assert inspect_text_geometry(page)["heading_status"] == "NOT_RUN"
        browser.close()


@pytest.mark.parametrize("risk", ["MEDIO", "ALTO", "BAJO"])
def test_risk_level_is_not_a_risk_explanation(app_module, risk):
    template = app_module.app.jinja_env.from_string(
        "{% from 'components/v937_sports_lifecycle.html' import professional_pick_brief %}{{ professional_pick_brief(pick) }}"
    )
    html = template.render(pick={"risk_level":risk,"risk":risk})
    assert "No hay un riesgo específico documentado" in html
    assert f"<p>{risk}</p>" not in html
    assert "Riesgo demostrado" in template.render(pick={"risk_note":"Riesgo demostrado"})


def test_closed_result_without_context_does_not_claim_result_is_missing(app_module):
    template = app_module.app.jinja_env.from_string(
        "{% from 'components/v937_sports_lifecycle.html' import learning_receipt %}{{ learning_receipt(pick) }}"
    )
    html = template.render(pick={"result_status":"won"})
    assert "Resultado registrado" in html
    assert "Todavía no existe un resultado evaluable" not in html
    assert "Todavía no existe un resultado evaluable" in template.render(pick={})
