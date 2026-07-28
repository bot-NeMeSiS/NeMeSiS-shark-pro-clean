# NeMeSiS Sports Experience - Roadmap futuro

Nota de producto, sin diseño ni implementación en este sprint.

Objetivo futuro: permitir consultar calendario, partidos, directos, alineaciones, jugadores, estadísticas, clasificaciones, H2H, equipos, competiciones, resultados y favoritos desde una experiencia deportiva propia.

La diferenciación prevista es combinar datos deportivos reales con SHARK, picks, Telegram, bankroll y análisis responsable. Cualquier desarrollo requerirá alcance, fuentes reales, presupuesto de API, privacidad, ciclo de vida deportivo y aprobación separados.

## Sports Core Foundation - Unified Domain Model

Estado local: integrado como base comun, sin deploy.

Contrato: SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1.

Impacto: Match Center, Live Story, Match Intelligence, SHARK y Telegram read-only ya pueden hablar el mismo idioma para partidos, equipos, competiciones, jugadores, eventos, evidencia y frescura.

Regla para siguientes sprints: Team Center, Competition Center y Player Center deben consumir estas entidades canonicas. No deben volver a normalizar nombres, estados o eventos por su cuenta.

## Competition Center Premium League Intelligence

Estado local: integrado y certificado con Browser QA desktop/tablet/mobile en DB temporal, sin deploy.

Contrato: COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1.

Impacto: la competicion ya dispone de una experiencia premium que consume Sports Core, Sports Knowledge Layer y Sports Graph. Muestra cabecera, clasificacion real cuando existe, calendario, equipos enlazados, contexto SHARK basado en evidencia, transparencia, frescura y limitaciones sin crear datos ficticios.

Siguiente modulo visible completado localmente: Player Center Premium Sports Identity. No comenzar Telegram Intelligence ni Sports Intelligence Gateway antes de cerrar Git de Player Center.

## SHARK Intelligence Platform

Estado local: integrado y validado con Browser QA desktop/tablet/mobile en DB temporal, sin deploy.

Contrato: SHARK-INTELLIGENCE-PLATFORM-V1.

Impacto: SHARK deja de ser solo una entrada aislada y pasa a funcionar como centro de inteligencia deportiva trazable. Consume Sports Core, Sports Knowledge Layer, Sports Graph Foundation, Match Intelligence, Team Center y Competition Center. Cada afirmacion expone fuente, evidencia, frescura, calidad y limitaciones. No hay conversacion IA generativa en esta fase, no se inventan datos y no se generan predicciones.

Siguiente modulo visible completado localmente: Player Center Premium Sports Identity. SHARK Intelligence ya queda consumido por Player Center sin IA generativa.
## User Intelligence Platform — PASS local pendiente de cierre Git

- Estado local: implementado sobre Sports Core, Sports Knowledge, Sports Graph, Match Intelligence y SHARK Intelligence.
- Contrato: `USER-INTELLIGENCE-PLATFORM-V1`.
- Privacidad: `USER-PRIVACY-CONTROLS-V1` con consulta, exportacion, reset, borrado y desactivacion.
- Alcance: prepara personalizacion futura; no cambia Home automaticamente, no usa IA generativa, no envia datos a terceros.
- Produccion: no certificada; no hubo push ni deploy.
## Player Center Premium Sports Identity

- Estado local: implementado y certificado con QA local completa, sin deploy.
- Contrato: `PLAYER-CENTER-PREMIUM-SPORTS-IDENTITY-PLATFORM-V1`.
- Impacto: NeMeSiS dispone de un centro de identidad deportiva del jugador que consume Player Entity, Sports Knowledge, Sports Graph, Match Intelligence, SHARK Intelligence y User Intelligence.
- Transparencia: fotografia, posicion, dorsal, lesiones, equipo, competicion o eventos ausentes permanecen como `No disponible` o informacion pendiente; no se inventan datos.
- Navegacion: conecta con Match Center, Team Center y Competition Center cuando existen entidades canonicas; los enlaces futuros se muestran como estados honestos.
- Produccion: no certificada; no hubo push ni deploy.

## Sports Intelligence Gateway

- Estado local: infraestructura implementada y validada localmente, sin deploy.
- Contrato: `SPORTS-INTELLIGENCE-GATEWAY-V1`.
- Impacto: toda fuente deportiva futura debe entrar por registro, compliance, health monitor y evidence registry antes de poder alimentar Sports Core, SHARK, Telegram, Team Center, Competition Center, Player Center o futuros modulos.
- Legal: no scraping masivo, no robots bypass, no paywall bypass, no copia de articulos, no reutilizacion de imagenes protegidas y no uso comercial sin aprobacion.
- Produccion: no certificada; no hubo push ni deploy.
## Decision Engine

- Estado local: infraestructura implementada y validada localmente, sin deploy.
- Contrato: `NEMESIS-DECISION-ENGINE-EVIDENCE-FIRST-V1`.
- Impacto: NeMeSiS dispone de una capa unica para organizar evidencia antes de que Telegram, Bankroll, Company OS, Match Center, Team Center, Competition Center o Player Center tomen decisiones visibles.
- Alcance: responde que sabemos, que no sabemos, que evidencia existe, que falta, que cambio, que fuentes coinciden, que fuentes discrepan, que calidad tiene cada dato y que confianza tiene la evidencia.
- Guardrails: no IA generativa, no predicciones, no picks, no llamadas externas, no escritura DB, no Telegram, no Stripe y no acciones automaticas.
- Produccion: no certificada; no hubo push ni deploy.
## Experience Platform

La experiencia deportiva pasa a tener una capa transversal de auditoria: exceso de scroll, espacios vacios, botones inconsistentes, textos tecnicos, estados vacios, navegacion incoherente y baja densidad se convierten en hallazgos priorizados antes de cualquier cambio visual. No aplica cambios automaticos.
