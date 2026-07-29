# Diccionario oficial de terminología

Este diccionario fija la forma visible oficial para NeMeSiS SHARK PRO. Los nombres internos pueden mantenerse en código cuando sean contratos existentes, pero la interfaz debe usar castellano coherente.

| Término interno o mixto | Término visible oficial | Uso |
| --- | --- | --- |
| Match | Partido | Cliente y admin |
| Match Center | Centro del partido | Nombre de pantalla |
| Match Intelligence | Inteligencia del partido | Inteligencia deportiva trazable |
| Team | Equipo | Cliente y admin |
| Team Center | Centro del equipo | Nombre de pantalla |
| Club | Club | Solo cuando el contexto sea futbolístico |
| Competition | Competición | Cliente y admin |
| Competition Center | Centro de la competición | Nombre de pantalla |
| Player | Jugador | Cliente y admin |
| Player Center | Centro del jugador | Nombre de pantalla |
| Sports Core | Modelo deportivo | Capa central visible |
| Unified Sports Domain Model | Modelo deportivo unificado | Admin/documentación |
| Sports Knowledge | Conocimiento deportivo | Admin y contexto deportivo |
| Sports Knowledge Layer | Capa de conocimiento deportivo | Admin/documentación |
| Sports Graph | Grafo deportivo | Admin/documentación |
| Sports Intelligence Gateway | Pasarela de inteligencia deportiva | Admin/documentación |
| Gateway | Pasarela | Admin/documentación |
| Decision Engine | Motor de decisiones | Admin/documentación |
| SHARK Intelligence | Inteligencia SHARK | Cliente y admin |
| User Intelligence | Inteligencia de usuario | Cliente y admin |
| Action Platform | Plataforma de acciones | Cliente y admin |
| Founder Dashboard | Panel fundador | Admin |
| Company Command Center | Centro de mando de empresa | Admin |
| Operations Center | Centro de operaciones | Admin |
| Developer Center | Centro de desarrollo | Admin |
| Company Board | Panel de empresa | Admin |
| Dashboard | Panel | Cliente y admin |
| Data Center | Centro de datos | Admin |
| Import Center | Centro de importación | Admin |
| Gateway source | Fuente de pasarela | Admin |
| Evidence | Evidencia | Cliente cuando aporta confianza; admin siempre |
| Freshness | Actualización | Cliente y admin |
| Quality | Calidad | Cliente y admin |
| Source | Fuente | Cliente y admin |
| Traceability | Trazabilidad | Admin |
| Readiness | Preparación | Admin |
| Production Readiness | Preparación de producción | Admin |
| Public Launch | Lanzamiento público | Admin |
| Go Live | Salida a producción | Admin |
| Sale Ready | Preparación comercial | Admin |
| Preview | Vista previa | Cliente y admin |
| Full company QA | QA integral de empresa | Admin |
| Cron | Cron | Admin, por ser término operativo aceptado |
| Master Tick | Master Tick | Admin, por ser nombre de contrato existente |
| Sentinel | Sentinel | Marca interna |
| AutoPilot | AutoPilot | Marca interna |
| Browser QA | Browser QA | Admin/documentación |
| Render | Render | Proveedor |
| Stripe | Stripe | Proveedor |
| Telegram | Telegram | Proveedor/canal |

## Reglas de uso

- En cliente se prioriza lenguaje funcional: partido, equipo, competición, picks, directo, calendario.
- En admin se permite lenguaje técnico cuando ayuda a operar, pero siempre con castellano alrededor.
- Las marcas internas se conservan si son nombres propios: SHARK, Sentinel, AutoPilot, Render, Stripe, Telegram y Codex.
- Los estados de evidencia se muestran sin traducir solo si forman parte de un contrato técnico; si son visibles al cliente, deben tener explicación en castellano.

## Términos prohibidos en interfaz cliente sin justificación

- Match
- Team
- Competition
- Player
- Gateway
- Engine
- Readiness
- Freshness
- Source
- Quality
- Evidence
- Dashboard

Si alguno debe aparecer por contrato, debe ir acompañado de una explicación visible.
