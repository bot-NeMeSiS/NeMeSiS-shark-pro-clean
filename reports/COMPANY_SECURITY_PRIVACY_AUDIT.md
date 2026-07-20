# NeMeSiS SHARK PRO - Auditoría de seguridad y privacidad

## Alcance y método

Revisión estática y pruebas locales aisladas. No se usaron secretos reales, no se tocaron cuentas reales y no se realizaron acciones externas. Los detalles que facilitarían abuso se omiten deliberadamente.

## Dictamen

**Madurez: 5/10.** Hay buenas bases (hash de contraseñas, CSRF, rate limit, firma Stripe, idempotencia, comparación constante y separación admin/cliente), pero existen brechas P0/P1 antes de una beta pública o de pago.

## Hallazgos prioritarios

| ID | Severidad | Hallazgo | Evidencia segura | Riesgo | Mitigación | Criterio de aceptación |
|---|---|---|---|---|---|---|
| SEC-01 | P0 potencial | Posible PII en repositorio público | 210 coincidencias de correo en reportes versionados; no se imprimieron ni clasificaron | Privacidad, reputación, legal | Triage autorizado, retirar lo real, evaluar historial/notificación | 100% clasificado y repo limpio |
| SEC-02 | P0 potencial | Patrones de asignación sensible en archivos históricos | 3 archivos; valores no revelados | Toma de cuentas/sistemas si fueran reales | Clasificar y rotar si procede | Scan actual/histórico y rotación documentados |
| SEC-03 | P1 | Secret Guard no ejecuta | Import ausente reproducible | Commits con secretos podrían pasar | Restaurar wrapper al motor oficial y test | CI falla ante canary y pasa limpio |
| SEC-04 | P1 | Webhook Telegram sin autenticación de origen demostrada | Solicitud sin firma aceptada en entorno aislado | Mensajes/acciones no autorizadas, abuso | Secret header, allowlist lógica y rate limit | Solicitud no autenticada 403 |
| SEC-05 | P1 | Secreto de automatización aceptado fuera de header | Código admite URL/form/JSON | Filtrado por logs, history y referrer | Solo header; deprecación compatible y logs redactados | URL/form/JSON rechazados |
| SEC-06 | P1 | Cookie de sesión no endurecida | `HttpOnly` sí; `Secure=false`, `SameSite` ausente local | Robo/cross-site session | Forzar Secure, HttpOnly, SameSite=Lax/Strict según flujo | Cabeceras efectivas en Render |
| SEC-07 | P1 | Restauración/borrado de backup sin doble control demostrado | Acciones admin críticas con sesión+CSRF | Pérdida/corrupción accidental | Reauth, confirmación tipada, doble aprobación y audit log | Restore drill y denial tests |
| SEC-08 | P2 | Endpoint runtime público demasiado verboso | Paths/ejecutable/flags internos | Reconocimiento y filtración de arquitectura | Allowlist pública mínima; detalle admin | Respuesta pública sin rutas internas |
| SEC-09 | P2 | GET con mutación | Regeneración Telegram permite GET | CSRF/crawlers/accidental mutation | Solo POST + CSRF + confirmación | GET 405 y POST protegido |
| SEC-10 | P2 | Webhook Stripe guarda payload inválido sin límite global demostrado | Persistencia antes/ante error y sin `MAX_CONTENT_LENGTH` visible | Crecimiento DB/retención de datos | Límite de cuerpo, redacción, retención | Payload grande rechazado sin write |
| SEC-11 | P2 | Sin CSP/HSTS observadas en capa app | Headers locales ausentes | XSS/downgrade defense incompleta | CSP en report-only y HSTS en producción TLS | Browser QA sin roturas y headers presentes |
| SEC-12 | P2 | Rate limit local y fail-open | SQLite por instancia y writes de eventos | Bypass multiinstancia/DB pressure | Rate limiter compartido o proxy; límites por ruta | Load test y bloqueo consistente |
| SEC-13 | P2 | Derechos de privacidad no operables | No se encontró flujo de borrado/exportación de cuenta | Incumplimiento y soporte manual | Runbook DSAR, verificación y audit trail | Solicitud de prueba completada |
| SEC-14 | P2 | Conexión SQLite abierta en Data Vault | Handle impide limpiar DB temporal | Locks/restore/backup inestable | Cerrar conexión en context manager | 100 ciclos sin handles/locks |

## Controles positivos

- Contraseñas no se almacenan en texto claro.
- CSRF está integrado en formularios mutantes normales.
- Login/registro/reset y envíos de prueba tienen rate limits.
- Stripe verifica firma y usa idempotencia.
- Comparación del secreto de automatización usa función constante.
- En Render, ausencia de clave principal está diseñada para fallar cerrada.
- Rutas admin aplican guard de sesión en la mayoría de superficies.
- HTML/API 500 intentan devolver mensajes seguros.
- `.gitignore` excluye DB/env/logs/ZIP, aunque no desversiona históricos ya tracked.

## Autenticación y autorización

Riesgos a probar antes de beta:

1. Matriz FREE/PRO/ELITE/ADMIN por endpoint, no solo por UI.
2. Invalidación de sesión después de logout/cambio de contraseña.
3. Rotación de `SECRET_KEY` con impacto documentado.
4. Cookie segura en HTTPS real.
5. Brute-force distribuido y recuperación de cuenta.
6. Acceso directo a APIs admin con sesión cliente.

## Datos personales y retención

Categorías potenciales: email/usuario, hash de contraseña, Telegram ID, Stripe customer/subscription IDs, actividad, favoritos, membresía, soporte, IP/eventos de seguridad.

Se necesita:

- Inventario de tratamiento y finalidad.
- Base legal y consentimiento aplicable.
- Retención por tabla/log/export/backup.
- Exportación y supresión verificadas.
- Minimización de IP y payloads.
- Política de acceso admin y logs de consulta.
- Procedimiento de breach y contacto DPO/legal.

## Backups y secretos

- Nunca guardar backups o exports con PII en GitHub.
- Cifrar backup off-site y separar llave del archivo.
- Rotar credenciales tras cualquier exposición confirmada.
- Mantener un inventario de secretos por servicio, owner, fecha y rotación, sin valores.
- No permitir secretos por URL.

## Seguridad de producto responsable

- Mantener +18, juego responsable y ausencia de garantía.
- No presentar score de calidad como probabilidad de ganar.
- Evitar dark patterns de upgrade.
- Revisión humana de claims, ROI y resultados.

## Decisión

No abrir beta pública/de pago hasta cerrar SEC-01 a SEC-07. Una beta privada gratuita puede considerarse después de clasificar exposición, endurecer endpoints/cookies y demostrar backup/restore.

