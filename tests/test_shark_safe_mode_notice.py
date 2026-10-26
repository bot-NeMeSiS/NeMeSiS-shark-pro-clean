from pathlib import Path


def test_shark_page_explains_actual_local_execution_regardless_of_key_presence():
    template = (Path(__file__).resolve().parents[1] / "templates" / "shark.html").read_text(encoding="utf-8")

    assert "{% if not assistant.get('generation_enabled') %}" in template
    assert 'data-shark-safe-mode="local-response"' in template
    assert "SHARK utiliza información registrada" in template
    assert "La generación externa todavía no está activada." in template
    assert "no inventará partidos, cuotas ni resultados" in template
