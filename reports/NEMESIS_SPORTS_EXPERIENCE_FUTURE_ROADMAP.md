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

Siguiente modulo visible: Player Center. No comenzar antes de aceptar el cierre local del Competition Center.

## SHARK Intelligence Platform

Estado local: integrado y validado con Browser QA desktop/tablet/mobile en DB temporal, sin deploy.

Contrato: SHARK-INTELLIGENCE-PLATFORM-V1.

Impacto: SHARK deja de ser solo una entrada aislada y pasa a funcionar como centro de inteligencia deportiva trazable. Consume Sports Core, Sports Knowledge Layer, Sports Graph Foundation, Match Intelligence, Team Center y Competition Center. Cada afirmacion expone fuente, evidencia, frescura, calidad y limitaciones. No hay conversacion IA generativa en esta fase, no se inventan datos y no se generan predicciones.

Siguiente modulo visible: Player Center. No comenzar antes de cerrar localmente SHARK Intelligence Platform.
## User Intelligence Platform — PASS local pendiente de cierre Git

- Estado local: implementado sobre Sports Core, Sports Knowledge, Sports Graph, Match Intelligence y SHARK Intelligence.
- Contrato: `USER-INTELLIGENCE-PLATFORM-V1`.
- Privacidad: `USER-PRIVACY-CONTROLS-V1` con consulta, exportacion, reset, borrado y desactivacion.
- Alcance: prepara personalizacion futura; no cambia Home automaticamente, no usa IA generativa, no envia datos a terceros.
- Produccion: no certificada; no hubo push ni deploy.
