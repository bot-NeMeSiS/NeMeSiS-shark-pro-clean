# NeMeSiS Sports Experience - Roadmap futuro

Nota de producto, sin diseño ni implementación en este sprint.

Objetivo futuro: permitir consultar calendario, partidos, directos, alineaciones, jugadores, estadísticas, clasificaciones, H2H, equipos, competiciones, resultados y favoritos desde una experiencia deportiva propia.

La diferenciación prevista es combinar datos deportivos reales con SHARK, picks, Telegram, bankroll y análisis responsable. Cualquier desarrollo requerirá alcance, fuentes reales, presupuesto de API, privacidad, ciclo de vida deportivo y aprobación separados.

## Sports Core Foundation - Unified Domain Model

Estado local: integrado como base comun, sin deploy.

Contrato: SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1.

Impacto: Match Center, Live Story, Match Intelligence, SHARK y Telegram read-only ya pueden hablar el mismo idioma para partidos, equipos, competiciones, jugadores, eventos, evidencia y frescura.

Regla para siguientes sprints: Team Center, Competition Center y Player Center deben consumir estas entidades canonicas. No deben volver a normalizar nombres, estados o eventos por su cuenta.
