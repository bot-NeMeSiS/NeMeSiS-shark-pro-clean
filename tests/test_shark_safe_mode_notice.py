from pathlib import Path


def test_shark_page_explains_safe_mode_when_openai_is_not_configured():
    template = (Path(__file__).resolve().parents[1] / "templates" / "shark.html").read_text(encoding="utf-8")

    assert "{% if not openai_ready %}" in template
    assert 'data-shark-safe-mode="openai-unconfigured"' in template
    assert "SHARK está en modo seguro" in template
    assert "La IA generativa externa no está configurada." in template
    assert "no inventará partidos, cuotas ni resultados" in template
