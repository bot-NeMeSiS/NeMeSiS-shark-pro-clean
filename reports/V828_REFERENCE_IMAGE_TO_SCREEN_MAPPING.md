# V828 Reference Image To Screen Mapping

Base oficial usada: `V827_REFERENCE_PHOTO_REBUILD_DESIGN_SYSTEM_FINAL`.

Referencia disponible: `C:\Users\aloha\OneDrive\Escritorio\imagenes bot proyecto.zip`, con 16 imágenes PNG. No se usó el ZIP viejo del chat como base del proyecto.

## Lectura visual común

Las imágenes de referencia comparten estos patrones:

- Sidebar/rail vertical fijo en escritorio, con logo grande, navegación por módulos y estado del sistema abajo.
- Topbar secundaria limpia, con buscador/acciones/usuario, sin repetir toda la navegación.
- Cards compactas, densas y con borde azul sutil.
- Métricas pequeñas, sin ceros gigantes ni paneles vacíos.
- Fondo dark premium, glow azul/cian y marca SHARK integrada.
- Admin más sobrio, tipo command center.
- Cliente y móvil con navegación simple, bottom nav única y SHARK sin duplicarse.

## Mapeo foto por foto

| Referencia | Pantalla objetivo | Ruta actual | Template | Diferencias detectadas | Cambio V828 |
|---|---|---|---|---|---|
| ChatGPT Image 20_47_44 (1) | dashboard/panel de control | `/admin/dashboard`, `/admin/control-center` | `admin_dashboard.html` | El admin real tenía topbar cargada y menor sensación de command center | Admin se mantiene separado, con cards compactas y shell sobrio V828 |
| ChatGPT Image 20_47_44 (2) | Telegram command center | `/admin/telegram/command-center` | `admin_telegram_command_center.html` | Faltaba acercar densidad, tabla y paneles a referencia | V828 compacta paneles/admin cards y conserva diagnósticos largos |
| ChatGPT Image 20_47_44 (3) | pagos/membresías/pricing | `/admin/payments`, `/admin/memberships`, `/membresias` | `admin_payments.html`, `admin_memberships.html`, `membership.html` | Planes y métricas necesitaban estilo más consistente | Cards y botones reciben tokens V828 |
| ChatGPT Image 20_47_44 (4) | centro de automatización | `/admin/daily-automation`, `/admin/automation-os` | `admin_daily_automation.html`, `admin_automation.html` | Paneles funcionales pero poco unificados | Admin shell V828 y compactación visual |
| ChatGPT Image 20_47_44 (5) | data marketplace/data center | `/admin/data-center` | `admin_data_center.html` | Exceso de bloques heredados | Cards admin densas y borde único |
| ChatGPT Image 20_47_44 (6) | lanzamientos/readiness | `/admin/final-certification` | `admin_final_certification.html` | Correcto en contenido, visual menos homogéneo | V828 aplica command center común |
| ChatGPT Image 20_47_44 (8) | picks y partidos | `/picks`, `/partidos`, `/calendar` | `picks.html`, `calendar.html` | Faltaba rail desktop y rows más densas | V828 crea rail cliente y rows compactas |
| ChatGPT Image 20_49_06 (1) | home/app cliente | `/`, `/app` | `home.html`, `client_app_center.html` | Portada y dashboard eran todavía demasiado abiertos | V828 refuerza fondo SHARK, grid y jerarquía |
| ChatGPT Image 20_49_06 (2) | directo/live | `/live`, `/directo` | `live.html` | Live tenía buenos datos pero menor densidad tipo Sofascore | V828 compacta live cards y scoreboard |
| ChatGPT Image 20_49_06 (3) | partidos | `/partidos`, `/calendar` | `calendar.html` | Lista deportiva necesitaba más estructura visual | V828 mejora rows, escudos, chips y ligas |
| ChatGPT Image 20_49_06 (4) | pick SHARK | `/picks`, `/shark` | `picks.html`, `shark.html` | Picks vendibles pero con demasiado aire | V828 refuerza card destacada y acciones |
| ChatGPT Image 20_49_06 (5) | detalle partido | `/match/<id>` | `match_detail.html` | Debe sentirse diferencial con equipos, SHARK y datos reales | V828 aplica shell/card system y conserva fallbacks |
| ChatGPT Image 20_49_06 (6) | histórico/track record | `/track-record` | `track_record.html` | Pantalla no debía quedar fuera de sistema | Marcado V828 y cards comunes |
| ChatGPT Image 20_49_06 (7) | elige tu plan/pricing | `/membresias`, `/admin/memberships` | `membership.html`, `admin_memberships.html` | Cards de planes requerían coherencia con admin/pagos | Estilo V828 sobre cards y CTAs |
| ChatGPT Image 20_49_06 (8) | mi cuenta/profile y Telegram cliente | `/profile`, `/telegram` | `profile.html`, `telegram.html` | Pantallas secundarias se veían menos premium | V828 shell, cards, botones y empty states |
| ChatGPT Image 20_49_06 (9) | soporte | `/support` | `support.html` | Soporte debía integrarse en ecosistema | Marcado V828 y estética común |

## Qué se modificó finalmente

- `templates/base.html`: versión, CSS cache busting, shell V828, rail cliente desktop, título seguro sin literal Jinja.
- `static/app.css`: capa V828 final con rail, topbar limpia, cards compactas, bottom nav móvil única, SHARK único, admin sobrio.
- Templates reales: marcado `data-v828-template` en pantallas cliente/admin cubiertas.

## Límites honestos

No se declara pixel-perfect porque no se generaron screenshots reales comparativos de navegador. Sí se inspeccionaron imágenes de referencia y se aplicó un sistema de paridad visual coherente.
