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


def test_canonical_navigation_contract_matches_current_language_and_legacy_layers_stay_purged():
    contract=read("templates/components/navigation_contracts.html")
    canonical=read("templates/components/v933_navigation.html")
    assert "Calendario" in contract and "Pronósticos" in contract and "Historial" in contract
    assert "('Partidos'," not in contract and "('Picks'," not in contract
    assert 'navigation_contracts.html' in canonical
    assert "nav_contracts.CLIENT_LINKS" in canonical
    assert "nav_contracts.ADMIN_LINKS" in canonical
    for legacy in ("v928_navigation.html","v930_navigation.html"):
        assert not (ROOT/"templates/components"/legacy).exists()

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

def test_founder_admin_copy_is_spanish_first():
    founder=(ROOT / "templates/admin_founder_dashboard.html").read_text(encoding="utf-8")
    os=(ROOT / "templates/admin_founder_os.html").read_text(encoding="utf-8")
    for forbidden in ("<strong>Scheduler</strong>", ">Product Review<", "<h2>Release Readiness</h2>", "<h2>Customer Overview</h2>"):
        assert forbidden not in founder
    for required in ("<strong>Programador</strong>", ">Revisión de producto<", "<h2>Preparación de publicación</h2>", "<h2>Resumen de clientes</h2>"):
        assert required in founder
    for forbidden in ("<h1>Founder Control</h1>", "Founder Inbox", "<h2>Founder Push</h2>", ">Company OS<", ">Inbox<"):
        assert forbidden not in os
    for required in ("<h1>Control fundador</h1>", "Bandeja del fundador", "<h2>Notificaciones del fundador</h2>", ">Sistema de empresa<", ">Bandeja<"):
        assert required in os


def test_launch_and_quality_admin_copy_is_spanish_first():
    go_live=(ROOT / "templates/admin_go_live.html").read_text(encoding="utf-8")
    quality=(ROOT / "templates/admin_quality_center.html").read_text(encoding="utf-8")
    review=(ROOT / "templates/admin_product_review_center.html").read_text(encoding="utf-8")
    assert "Track Record" not in go_live and "Historial" in go_live
    assert "Live / finalizados" not in quality and "Directo / finalizados" in quality
    assert "Picks publicados" not in quality and "Pronósticos publicados" in quality
    assert "Total picks:" not in quality and "Total pronósticos:" in quality
    assert "Product Review Center" not in review
    assert "Centro de revisión de producto" in review
    assert "Resumen de revisión de producto" in review


def test_sale_and_client_experience_admin_copy_is_spanish_first():
    client=(ROOT / "templates/admin_client_experience.html").read_text(encoding="utf-8")
    sale=(ROOT / "templates/admin_sale_ready.html").read_text(encoding="utf-8")
    gtm=(ROOT / "templates/admin_go_to_market_office.html").read_text(encoding="utf-8")
    assert "Home, Directo, Calendario, Picks, Combis, SHARK, Telegram y Match Detail" not in client
    assert "Inicio, Directo, Calendario, Pronósticos, Combinadas, SHARK, Telegram y detalle de partido" in client
    for forbidden in ("Live QA", "Track Record", "<h3>Live</h3>", "<h3>Picks</h3>", "picks decididos", "picks registrados.", "Abrir picks"):
        assert forbidden not in sale
    for required in ("QA de Directo", "Historial", "<h3>Directo</h3>", "<h3>Pronósticos</h3>", "pronósticos decididos", "pronósticos registrados.", "Abrir pronósticos"):
        assert required in sale
    assert "Release Readiness" not in gtm
    assert "Top 20 acciones antes de Release 1.0" not in gtm
    assert "Preparación de publicación" in gtm
    assert "Top 20 acciones antes de la publicación 1.0" in gtm


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
        "templates/admin_dashboard.html": ["<p class=\"eyebrow\">Picks</p>", "Respuesta dry-run segura"],
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
    realtime=read("templates/admin_realtime_center.html")
    dashboard=read("templates/admin_dashboard.html")
    automation=read("templates/admin_automation_center.html")
    for token in ("Reglas V845","Telegram V844"):
        assert token not in dashboard
    assert "SHARK Admin AI" in dashboard
    assert "Las propuestas no se ejecutan hasta que las apruebas." in dashboard
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


def test_secondary_client_surfaces_use_current_spanish_vocabulary():
    hub=read("templates/unified_intelligence_hub.html")
    markets=read("templates/betting_markets.html")
    world=read("templates/world_cup_launch.html")
    dynamic=read("templates/dynamic_mode.html")
    briefing=read("templates/daily_briefing.html")
    for token in ("Intelligence Hub","Score personal","Zero click",">Picks</a>","Combis","Builder"):
        assert token not in hub
    assert "Centro de inteligencia" in hub and "Pronósticos visibles" in hub and 'href="/combinadas"' in hub
    for token in ("ver un pick",">Ver picks</a>","Combis","Partidos con pick","sobre picks reales"):
        assert token not in markets
    assert "Ver pronósticos" in markets and "Combinadas recomendadas" in markets and 'href="/combinadas"' in markets
    for token in ("directos, picks",">Picks</a>",">Histórico</a>","<span>Picks</span>","Picks vinculados","No hay picks Mundial"):
        assert token not in world
    assert "Pronósticos vinculados" in world and ">Historial</a>" in world
    for token in ("directo, picks",">Picks</a>","<span>Picks</span>","competición, picks","directo o picks"):
        assert token not in dynamic
    assert ">Pronósticos</a>" in dynamic
    assert ">Picks</a>" not in briefing and "<h2>Picks y análisis</h2>" not in briefing
    assert ">Pronósticos</a>" in briefing and "<h2>Pronósticos y análisis</h2>" in briefing
