"""V941 product language clarity for core client/admin surfaces."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT/path).read_text(encoding="utf-8")

def test_client_navigation_and_history_use_clear_spanish():
    nav=read("templates/components/v933_navigation.html")
    history=read("templates/track_record.html")
    assert "Historial" in nav and "Histórico" not in nav
    assert "Rentabilidad (ROI)" in history
    assert "Acierto" in history
    assert "Unidades recomendadas" in history
    assert "grading" not in history
    assert "Winrate" not in history

def test_legacy_navigation_layers_match_current_language():
    for path in ("templates/components/v928_navigation.html","templates/components/v930_navigation.html"):
        text=read(path)
        assert "Calendario" in text and "Pronósticos" in text and "Historial" in text
        assert ">Partidos<" not in text and ">Picks<" not in text

def test_admin_pronosticos_use_clear_editorial_language():
    text=read("templates/admin_picks.html")
    for forbidden in ("Track Record","Winrate","Buscar pick","Nuevo pick","Stake (u)","Data Trust"):
        assert forbidden not in text
    assert "Historial" in text and "Acierto" in text and "Unidades recomendadas" in text and "Calidad de datos" in text

def test_admin_data_and_telegram_remove_unexplained_jargon():
    data=read("templates/admin_data_center.html")
    telegram=read("templates/admin_telegram_command_center.html")
    for forbidden in ("Scheduler","Última sync","Errores scheduler","Warmup seguro"):
        assert forbidden not in data
    for forbidden in ("Dry-run · sin envío","Dedupe","Quiet hours","Auto picks/día","Picks elegibles","Data Trust"):
        assert forbidden not in telegram
    assert "Simulación · sin envío" in telegram and "Horas de silencio" in telegram

def test_internal_systems_lead_with_human_labels():
    nav=read("templates/components/v933_navigation.html")
    company=read("templates/admin_company_os.html")
    release=read("templates/admin_final_release.html")
    assert "Calidad / Sentinel" in nav
    assert "Versión / Producción" in nav
    assert "Sistema operativo de NeMeSiS SHARK PRO" in company
    assert "Candidata de publicación comercial" in release


def test_admin_master_uses_clear_operational_language_and_exposes_install():
    text=read("templates/admin_dashboard.html")
    for forbidden in ("Gestionar picks","Telegram dry-run","Founder ·","Company OS","AutoPilot y workflow","Release y producción","<option value=\"matches\">Partidos</option>","<option value=\"picks\">Picks</option>"):
        assert forbidden not in text
    assert "Gestionar pronósticos" in text
    assert "Simular Telegram" in text
    assert "Instalar NeMeSiS en este dispositivo" in text
    assert "data-admin-pwa-install" in text
    assert 'data-action="pwa-install"' in text
