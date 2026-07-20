# NeMeSiS SHARK PRO - Auditoría ejecutiva de empresa

Fecha de corte (Madrid): 2026-07-19

## Dictamen

**Estado general: AMARILLO. Producción: NO CERTIFICADA en esta ejecución.**

NeMeSiS SHARK PRO ya es un producto deportivo reconocible, coherente y visualmente avanzado. Tiene controles de calidad poco habituales para su tamaño: validación de rutas, filtros anti-dato falso, Sentinel, Browser QA, versionado de runtime, guardas de APIs y una disciplina explícita de no inventar actividad deportiva. La experiencia visual local puede enseñarse en una beta controlada.

Todavía no opera como una empresa preparada para aceptar clientes de pago a escala. Los principales límites no son de diseño: son privacidad del repositorio público, recuperación de datos no demostrada, seguridad de endpoints operativos, pipeline de seguridad roto, pagos/Telegram no certificados de extremo a extremo y dependencia excesiva de una sola persona y de un monolito.

## Qué empresa existe realmente

NeMeSiS es hoy una **plataforma Flask monolítica, orientada a criterio deportivo**, con cuatro superficies:

1. Producto público y PWA.
2. Experiencia autenticada de cliente.
3. Centro operativo de administración.
4. Automatización de datos, picks, Telegram, SHARK, pagos y observabilidad.

La propuesta distintiva es sólida: mostrar únicamente información que supera una puerta de calidad y explicar por qué se publica o se descarta. Ese posicionamiento reduce el riesgo de parecer una casa de apuestas y convierte la transparencia en producto.

## Fortalezas confirmadas

| Fortaleza | Evidencia | Valor empresarial |
|---|---|---|
| Identidad visual propia | Capturas desktop/móvil coherentes | Producto reconocible y presentable. |
| Datos seguros por defecto | Checks de falso-live, stale y picks incompletos | Reduce daño reputacional. |
| Rutas y navegación amplias | 664 reglas, 929 enlaces auditados | Cobertura funcional extensa. |
| Sentinel estático | 10.0, 0 incidencias en su alcance | Prevención básica continua. |
| Browser QA | 238 capturas históricas | Evidencia visual reproducible. |
| Compatibilidad SQLite | DB moderna, legacy, vacía y bloqueada | Mayor resiliencia de lectura. |
| SHARK eficiente en candidato | 18.9 ms mediana local, sin writes ni red | Buen diseño de render seguro. |
| Stripe con firma e idempotencia | Código y test temporal | Base técnica correcta para pagos. |
| PWA con invalidación de caché | `NEMESIS_CACHE_V937` y navegación network-first | Menor riesgo de HTML obsoleto. |
| Conducta responsable | Copy, estados seguros y ausencia de datos sintéticos | Confianza y diferenciación. |

## Riesgos que impiden una apertura comercial plena

### P0

1. **Exposición potencial de privacidad en repositorio público.** Hay 210 coincidencias de correo en reportes versionados y tres archivos con patrones de asignación sensible. No se imprimieron valores ni se confirma que sean reales, pero la mera posibilidad exige triage inmediato.
2. **Recuperación ante pérdida de disco no demostrada.** DB y backups parecen compartir `/data`; no existe evidencia de copia off-site ni de restore drill real. Además, Data Vault dejó una conexión SQLite abierta en una prueba temporal.

### P1

- Secret Guard no importa y, por tanto, el control de secretos actual no es ejecutable.
- Webhook Telegram acepta solicitudes sin autenticación de origen.
- Credencial de automatización puede viajar por query string/form/JSON.
- Cookies de sesión no fuerzan `Secure`/`SameSite` en la respuesta local.
- Stripe, webhooks, cancelación y membresías reales no están certificados.
- Datos deportivos, 5xx, DB y cron actuales de Render no se pudieron certificar.
- Legal, responsable del servicio, jurisdicción y textos comerciales siguen pendientes de revisión.
- ELITE+ no es un tier técnico independiente aunque se presenta como parte del catálogo.
- `main` no contiene los cambios candidatos de pipeline y SHARK observados en PR abiertos.
- Restaurar/borrar backups es una operación administrativa crítica sin reautenticación o doble control demostrado.

## Capacidad operativa

| Capacidad | Nota | Lectura ejecutiva |
|---|---:|---|
| Detectar fallos | 6/10 | Muchos checks locales, poca alerta externa y cobertura desigual. |
| Contener fallos | 6/10 | Fallbacks y puertas de calidad útiles; kill switches y mantenimiento no están unificados. |
| Recuperarse | 4/10 | Hay código de backup, pero no prueba off-site/restauración real. |
| Operar sin intervención | 5/10 | Un cron deportivo declarado; resto de automatización no demostrado en Render. |
| Vender con confianza | 5/10 | Producto visual listo para beta, pagos/legal/soporte aún no. |
| Escalar | 4/10 | SQLite, un worker Gunicorn, monolito y falta de telemetría limitan crecimiento. |

## Decisión de lanzamiento

- **Demo privada guiada:** sí, con datos y cuentas de prueba.
- **Beta privada gratuita:** condicional, tras cerrar los P0 y certificar producción actual.
- **Beta de pago:** no.
- **Lanzamiento público:** no.

## Prioridad ejecutiva

La siguiente acción no es añadir producto. Es ejecutar una **clasificación de privacidad y secretos del repositorio público**, retirar o rotar lo que resulte real mediante un procedimiento autorizado y dejar una evidencia de cierre. Después: backup off-site/restauración, producción read-only, pagos/Telegram y observabilidad.

## Qué no se modificó

- Producción, Render, GitHub, ramas y PR.
- DB real o usuarios.
- Telegram y Stripe.
- Secretos o configuración.
- Versión V937.

