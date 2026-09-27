"""V941 product language clarity for core client/admin surfaces."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT/path).read_text(encoding="utf-8")

def test_client_navigation_and_history_use_clear_spanish():
    nav=read("templates/components/navigation_contracts.html")
    history=read("templates/track_record.html")
    assert "Historial" in nav and "Histórico" not in nav
    assert "Rentabilidad (ROI)" in history
    assert "Acierto" in history
    assert "Unidades registradas" in history
    assert "grading" not in history
    assert "Winrate" not in history

def test_canonical_navigation_uses_spanish_plan_route_and_page_state():
    nav=read("templates/components/v933_navigation.html")
    assert 'href="/memberships"' not in nav
    assert 'href="/membresias"' in nav
    assert 'aria-current="true"' not in nav
    assert 'aria-current="page"' in nav


def test_legacy_navigation_layers_match_current_language():
    contract=read("templates/components/navigation_contracts.html")
    assert "Calendario" in contract and "Pronósticos" in contract and "Historial" in contract
    assert "('Partidos'," not in contract and "('Picks'," not in contract
    for path in ("templates/components/v928_navigation.html","templates/components/v930_navigation.html"):
        text=read(path)
        assert 'navigation_contracts.html' in text
        assert "nav_contracts.CLIENT_LINKS" in text

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
    for forbidden in ("Dry-run · sin envío",">Dedupe<","Quiet hours","Auto picks/día","Picks elegibles","Data Trust"):
        assert forbidden not in telegram
    assert "Simulación · sin envío" in telegram and "Horas de silencio" in telegram and "Duplicado" in telegram

def test_internal_systems_lead_with_human_labels():
    nav=read("templates/components/navigation_contracts.html")
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


def test_canonical_surfaces_remove_legacy_product_words():
    checks={
        "templates/home.html": ["<strong>LIVE</strong>", 'ui("Picks")', "quick_action('Picks'", "quick_action('Histórico'", "Sports first"],
        "templates/picks.html": ["'Histórico real'", "quick_action('Ver histórico'"],
        "templates/admin_realtime_center.html": ["Picks y cuotas", "Abrir picks", "Sin picks completos", "<strong>Con live</strong>", "Última sync"],
        "templates/admin_shark_center.html": ["<p class=\"eyebrow\">Picks</p>", "Respuesta dry-run segura"],
        "templates/admin_system.html": ["kpi_card('Picks'", "quick_action('Partidos'", "cache y jobs", "Identidad del runtime"],
        "templates/admin_telegram_command_center.html": ["command center", "dedupe", "<h2>Dry-run</h2>", "Sin preview generado.", "<strong>Auto send</strong>"],
    }
    for path,forbidden in checks.items():
        text=read(path)
        for token in forbidden:
            assert token not in text, (path,token)

def test_legacy_client_maps_use_canonical_plain_language():
    menu=read("templates/client_menu.html")
    nav_map=read("templates/client_navigation_map.html")
    assert "Cuota, stake" not in menu
    assert "<strong>Histórico</strong>" not in menu
    assert "→ Histórico" not in menu
    assert "Cuota, unidades" in menu and "<strong>Historial</strong>" in menu
    assert "<span>Pick</span>" not in nav_map
    assert "<span>Partido</span>" not in nav_map
    assert "<span>Pronóstico</span>" in nav_map and "<span>Calendario</span>" in nav_map


def test_calendar_uses_pronostico_for_pick_filter_label():
    text=read("templates/calendar.html")
    assert "kpi_card('Con pronóstico'" in text
    assert "kpi_card('Con pick'" not in text

def test_admin_plan_language_is_clear():
    memberships=read("templates/admin_memberships.html")
    users=read("templates/admin_users.html")
    assert "Planes temporales" in memberships
    assert "Guardar plan" in users


def test_plan_and_payment_surfaces_separate_access_from_revenue():
    payments=read("templates/admin_payments.html")
    plans=read("templates/admin_memberships.html")
    assert "Pagos y suscripciones" in payments
    assert "Accesos manuales" in payments
    assert "Los planes manuales o regalados no se suman a MRR ni conversión." in payments
    assert "Solo Stripe activo" in payments
    assert "Planes y accesos" in plans

def test_membership_product_labels_use_current_vocabulary():
    membership=read("engines/membership_engine.py")
    experience=read("engines/membership_experience_engine.py")
    stripe=read("engines/stripe_payments_engine.py")
    for forbidden in ("Picks PRO","Picks ELITE","Auto Picks completo"):
        assert forbidden not in membership
    assert "Pronósticos PRO" in membership and "Pronósticos ELITE" in membership
    assert "Track record" not in experience
    assert "Abrir command center" not in experience
    assert "Alertas live" not in stripe


def test_shark_surface_uses_current_product_language():
    text=read("templates/shark.html")
    for forbidden in ("{'label':'Partidos'","{'label':'Ver picks'","Explorar partidos","Revisar picks","<strong>Pick</strong>","Sin pick real publicado","Picks completos","Abrir partidos","Calidad y dedupe"):
        assert forbidden not in text
    assert "Calendario" in text and "Ver pronósticos" in text
    assert "Pronósticos completos" in text and "Abrir calendario" in text and "Calidad y duplicados" in text


def test_admin_primary_actions_use_canonical_product_names():
    dashboard=read("templates/admin_dashboard.html")
    picks=read("templates/admin_picks.html")
    assert "Sincronizar calendario" in dashboard and "Sincronizar partidos" not in dashboard
    assert "Abrir historial" in picks and "Abrir histórico" not in picks


def test_home_error_history_and_admin_tools_avoid_internal_jargon():
    home=read("templates/home.html")
    history=read("templates/track_record.html")
    not_found=read("templates/404.html")
    app_source=read("app.py")
    automation=read("templates/admin_automation_center.html")
    automation_engine=read("engines/automation_orchestrator_engine.py")
    users=read("templates/admin_users.html")
    payments=read("templates/admin_payments.html")
    for token in ("Smart Home","Briefing","Recap","Live real","Match Center","Sports Relevance","Intelligence"):
        assert token not in home
    assert "Cómo calculamos el historial" in history
    assert "El histórico empieza" not in history
    assert "app/PWA" not in not_found
    assert '{"label": "Picks", "href": "/picks"}' not in app_source
    assert "Revisa logs Render" not in app_source
    for token in ("scheduler_engine legacy tasks","highlights sync","standalone pick grading","visual/browser QA workers","Browser QA","Data Vault y retención"):
        assert token not in automation + automation_engine
    assert "Planes y accesos" in users and "Membresías con fecha" not in users
    assert "Ingresos mensuales estimados (MRR)" in payments
    assert "Confirmación Stripe" in payments


def test_data_center_distinguishes_legacy_scheduler_from_real_automation():
    text=read("templates/admin_data_center.html")
    assert "Programador interno de compatibilidad" in text
    assert "No es el cron de producción" in text
    assert "Centro de Automatización" in text
    assert "<h2>Tareas automáticas</h2>" not in text


def test_system_uses_canonical_admin_routes_and_plain_language():
    text=read("templates/admin_system.html")
    assert "Partidos guardados" in text
    assert "Tareas recurrentes y bajo demanda" in text
    assert "/admin/sentinel-issues" in text
    assert "/admin/autonomous-company-sentinel" not in text


def test_final_release_does_not_overclaim_or_show_stale_version_label():
    text=read("templates/admin_final_release.html")
    assert "{{ app_version }} · Candidata de publicación comercial" in text
    assert "V738 · Candidata" not in text
    assert "Candidata preparada para validación comercial" in text
    assert "Versión final preparada para vender con control" not in text
    assert "Revisar salida a producción" in text


def test_canonical_admin_surfaces_hide_historical_version_labels_and_runtime_jargon():
    shark=read("templates/admin_shark_center.html")
    realtime=read("templates/admin_realtime_center.html")
    dashboard=read("templates/admin_dashboard.html")
    automation=read("templates/admin_automation_center.html")
    for token in ("Reglas V845","Telegram V844"):
        assert token not in shark
    assert "Reglas de seguridad de SHARK" in shark
    assert "durante el render" not in realtime
    assert "base de datos y caché" in realtime
    assert "desde este runtime" not in dashboard
    assert "desde este entorno" in dashboard
    assert "Tareas recurrentes reales" in automation
    assert "Procesos internos" in automation


def test_client_section_ctas_use_canonical_section_names():
    picks=read("templates/picks.html")
    assert "quick_action('Abrir calendario'" in picks
    assert "quick_action('Explorar partidos'" not in picks


def test_client_home_account_and_plan_copy_avoid_legacy_pick_jargon_and_overclaims():
    home=read("templates/client_app_center.html")
    account=read("templates/account_center.html")
    app_source=read("app.py")
    for token in ("Picks activos","Pick destacado","Todavía no hay picks publicados"):
        assert token not in home
    assert "Pronósticos activos" in home and "Pronóstico destacado" in home
    assert "Alertas, picks y resúmenes" not in account
    assert "Partidos, equipos o picks guardados" not in account
    for token in (
        "Pronósticos automáticos y SHARK completo",
        "combinadas automáticas, value avanzado, top picks",
        "Pronósticos automáticos, combinadas avanzadas",
        '"Picks y señales"',
        '"Insight SHARK"',
    ):
        assert token not in app_source
    assert "Acceso ELITE y SHARK ampliado" in app_source
    assert '"Pronósticos y contexto"' in app_source


def test_pick_cards_present_analysis_score_as_index_not_probability():
    components=read("templates/components/v933_ui.html")
    picks=read("templates/picks.html")
    assert "Confianza del análisis" not in components
    assert "Índice del análisis" in components
    assert "no es probabilidad de acierto" in components
    assert "/100" in components
    assert ">Stake <" not in components
    assert "Unidades orientativas" in components
    assert 'ui("Pronósticos")' in components
    assert "status_chip('Controlado','success')" not in picks
    assert "status_chip('Revisado','blue')" in picks


def test_membership_page_does_not_present_unconfigured_price_as_purchasable():
    text=read("templates/membership.html")
    assert "Precio pendiente" in text
    assert "plan.get('configured')" in text
    assert "Configuración pendiente" in text


def test_client_telegram_never_promises_delivery_when_channel_is_not_ready():
    text=read("templates/telegram.html")
    assert "telegram_ready = state.get('linked') and channel_enabled" in text
    assert "Lo que recibirás en tu canal" not in text
    assert "Contenido previsto para tu plan" in text
    assert "Pronósticos premium" not in text
    assert "Pronósticos disponibles" in text
    assert "Esta pantalla no envía mensajes por sí sola" in text
    assert "status_chip('Listo' if telegram_ready else 'En espera'" in text


def test_membership_benefits_are_conditional_and_payment_copy_is_plain_spanish():
    text=read("templates/membership.html")
    for token in ("Experiencia completa","Prioridad y acceso avanzado","Alertas prioritarias","Acceso anticipado a funciones",">Checkout<"):
        assert token not in text
    assert "Pronósticos PRO cuando estén publicados" in text
    assert "Funciones ELITE cuando estén habilitadas" in text
    assert "Pago seguro" in text
    assert "Pago pendiente de configuración" in text


def test_legacy_membership_catalog_matches_current_product_truth():
    app_source=read("app.py")
    for token in (
        '"price": "Premium"',
        '"price": "Top"',
        '"Picks premium"',
        '"Combis"',
        '"IA SHARK"',
        '"Briefings"',
        '"Prioridad live"',
        'f"/memberships?plan={target}"',
    ):
        assert token not in app_source
    assert '"price": "Precio según configuración"' in app_source
    assert '"Pronósticos PRO publicados"' in app_source
    assert '"Pronósticos ELITE publicados"' in app_source
    assert 'f"/membresias?plan={target}"' in app_source


def test_visible_surfaces_use_canonical_spanish_routes():
    hub=read("templates/unified_intelligence_hub.html")
    home=read("templates/home.html")
    base=read("templates/base.html")
    error_500=read("templates/500.html")
    company=read("templates/company_platform.html")
    assert 'href="/menu"' not in hub
    assert 'href="/app"' in hub
    assert 'href="/memberships"' not in home
    assert 'href="/membresias"' in home
    for text in (base,error_500,company):
        assert 'href="/support"' not in text
        assert 'href="/soporte"' in text
