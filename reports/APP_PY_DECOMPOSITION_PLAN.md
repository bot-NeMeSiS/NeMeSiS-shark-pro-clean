# APP.PY Decomposition Plan

Estado: `PLAN_READY`, sin extracción de alto riesgo en este cierre.

## Evidencia actual

- `app.py`: 29.970 líneas y 1.393 funciones.
- Decoradores de ruta detectados en `app.py` y blueprints: 779 en análisis textual; 789 reglas estáticas únicas; 807 reglas runtime incluyendo `static` y aliases registrados.
- Renderizados directos: 170 llamadas a `render_template`.
- El 98,6 % de las vistas runtime siguen perteneciendo al módulo `app`; existen 4 blueprints y 6 servicios.
- La aplicación mantiene contratos activos de auth, Sports P0, SHARK, Growth, Telegram, Continuous Evolution y Founder Center. Extraerlos juntos sería un Big Bang sin beneficio proporcional.

## Qué debe quedarse por ahora

1. Creación de `Flask app`, carga de configuración y registro de blueprints.
2. Compatibilidad de endpoints y aliases públicos que ya tienen consumidores.
3. Filtros Jinja y adaptadores mínimos que requieren acceso al contexto Flask.
4. Inicialización de extensiones, sesiones, CSRF y hooks de request/response.
5. Composición final de dependencias mientras cada dominio no tenga una interfaz estable probada.

## Qué puede moverse de forma segura

| Orden | Bloque | Destino propuesto | Riesgo | Cobertura necesaria |
|---|---|---|---|---|
| 1 | Diagnósticos read-only y respuestas de health/version | `blueprints/operations.py` | Bajo | health, runtime SHA, secret guard |
| 2 | Páginas legales y contenido público estático | `blueprints/public.py` | Bajo | rutas, canonical, links, derechos |
| 3 | Helpers puros de presentación Madrid/estado | `services/presentation.py` | Bajo-medio | tests unitarios de zona horaria y status |
| 4 | APIs admin read-only | `blueprints/admin_read.py` | Medio | auth backend, 403/302, Browser QA admin |
| 5 | Growth/Revenue read-only | `blueprints/growth.py` | Medio | contratos de funnel y datos no ficticios |
| 6 | Continuous Evolution endpoint y vistas | `blueprints/evolution.py` | Medio | safe mode, auth, idempotencia, storage |
| 7 | Vistas Sports que ya consumen Sports Core | `blueprints/sports.py` | Alto | Sports P0 completa y consistencia cross-screen |
| 8 | Auth, usuarios, membresías y escrituras | mantener hasta sprint dedicado | Muy alto | transacciones, CSRF, permisos, rollback DB |

## Secuencia de extracción

Cada extracción debe mover un único dominio, preservar endpoint y nombre de ruta, y dejar un adaptador temporal en `app.py` solo si un import externo lo necesita. El gate mínimo por bloque es: `py_compile`, pytest completo, rutas/enlaces, Golden Journeys, auth separation y Browser QA de las superficies afectadas.

No se deben mover Sports, SHARK, Telegram, membresías o automatización en la misma entrega. Tampoco se deben renombrar endpoints públicos durante la extracción.

## Dependencias a resolver antes

- Convertir accesos globales a DB/config en interfaces explícitas de lectura o escritura.
- Separar helpers puros de funciones que dependen de `request`, `session`, `g` o side effects.
- Mantener una tabla de ownership por dominio y un test de unicidad de reglas.
- Sustituir comprobaciones históricas de versión por contratos de comportamiento.

## Criterio de éxito

Reducir `app.py` gradualmente sin cambiar capacidades, URLs ni seguridad. El objetivo del siguiente bloque seguro no es un número de líneas: es trasladar un dominio read-only con ownership claro y cero regresiones.
