from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


def test_product_excellence_top100_markers_are_present():
    checks = {
        "templates/home.html": ['data-top100-improvement="2,3,19"', "Primer valor en menos de un minuto", "Abrir calendario", "Abrir briefing"],
        "templates/shark.html": ['data-top100-improvement="4"', "C\u00f3mo leer SHARK", "Riesgo visible"],
        "templates/membership.html": ['data-top100-improvement="5,6"', "Elige por lo que quieres resolver", "Comparar ELITE"],
        "templates/telegram.html": ['data-top100-improvement="5"', "Vista previa premium", "esta vista no env\u00eda Telegram real"],
        "templates/picks.html": ['data-top100-improvement="8"', "Antes de decidir", "stake es orientativo"],
        "templates/action_platform.html": ["state_labels", "Verificaci\u00f3n parcial", "tu d\u00eda deportivo"],
        "templates/404.html": ['data-top100-improvement="31"', "Siguiente paso recomendado"],
        "templates/500.html": ['data-top100-improvement="31"', "Soporte"],
    }
    for file_name, snippets in checks.items():
        text = read_text(file_name)
        for snippet in snippets:
            assert snippet in text


def test_product_excellence_visible_copy_has_no_known_mojibake_regressions():
    files = [
        "templates/404.html",
        "templates/500.html",
        "templates/action_platform.html",
        "templates/home.html",
        "templates/membership.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/telegram.html",
    ]
    bad_fragments = [
        "contin?",
        "navegaci?",
        "Ning?",
        "informaci?",
        "Verificaci?",
        "revisi?",
        "Hip?",
        "competici?",
        "d?a",
        "pr?ctica",
        "presi?",
        "est? confirmada",
        "estimaci?",
        "selecci?",
        "hist?rico",
        "C?mo",
        "?til",
        "qu? cambia",
        "conclusi?",
        "As?",
        "env?a",
        "?" * 8,
        chr(0xFFFD),
    ]
    for file_name in files:
        text = read_text(file_name)
        for fragment in bad_fragments:
            assert fragment not in text


def test_product_excellence_accessibility_and_mobile_touch_rules_exist():
    css = read_text("static/v933-product.css")
    assert "Product Excellence Sprint 01" in css
    assert ":focus-visible" in css
    assert "min-height: 44px" in css
    assert "v933-telegram-preview-card" in css
    assert "ns-next-step" in css
