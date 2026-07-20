# V938 Findings Evidence Classification

Esta matriz evita convertir hipótesis en fallos. Los estados permitidos son: **CONFIRMADO**, **NO CERTIFICADO**, **HIPÓTESIS**, **BLOQUEADO POR ACCESO** y **REQUIERE REVISIÓN**.

| Área | Estado | Evidencia local | Tratamiento V938 |
|---|---|---|---|
| Base V937 y SHA `3102618e…` | CONFIRMADO | `VERSION.txt`, `APP_VERSION`, `.git/HEAD` y refs locales | Preservar y versionar hacia V938 |
| Secret Guard importable | CONFIRMADO | `check_v915` y `reporting_worker` importan un módulo inexistente | Crear wrapper que delega en el escáner oficial V938; no desactivar el gate |
| Telegram webhook sin firma | CONFIRMADO | POST `/telegram/webhook` procesa JSON sin autenticar la firma | Añadir validación compatible y reportar configuración pendiente |
| Secret de automatización en query/form/JSON | CONFIRMADO | `automation_request_secret()` acepta cuatro transportes, incluido query string | Mantener compatibilidad legacy, marcar deprecación y exigir header en el endpoint V938 |
| Cookies de sesión endurecidas explícitamente | CONFIRMADO | No existe configuración explícita Secure/SameSite en `app.py` | Añadir HttpOnly/SameSite y Secure en entorno productivo, sin romper test local |
| Cierre fiable de conexiones Data Vault | CONFIRMADO | Las conexiones de solo lectura se usan con context manager sin cierre explícito | Cerrar conexiones de forma determinista y añadir regresión |
| Base de datos local accesible | CONFIRMADO | Auditoría local previa e integridad SQLite local | Mostrar estado local; no extrapolar a producción |
| DB persistente de Render | BLOQUEADO POR ACCESO | Sin lectura autorizada del runtime/disco de Render en esta ejecución | Mostrar como no certificado, nunca como caída |
| Backups locales detectables | CONFIRMADO | `data_vault_engine` lista y valida metadatos/hash | Separar existencia, validez y restauración probada |
| Backup externo/offsite | NO CERTIFICADO | No hay evidencia local de destino externo independiente | Diseñar adaptador y readiness; no simular copia externa |
| Restore aislado probado | NO CERTIFICADO | No hay evidencia de ensayo de restauración reciente | Proveer verificador aislado y runbook, sin tocar DB real |
| Runtime Render V937/V938 | BLOQUEADO POR ACCESO | No se consulta producción en esta fase | Mantener gate bloqueado hasta evidencia externa |
| GitHub/CI remoto | BLOQUEADO POR ACCESO | No hay herramienta Git/GitHub operativa en esta sesión | No modificar ni inferir estado remoto |
| Sentinel local | CONFIRMADO | Motores y checks existentes, memorias runtime presentes | Integrar lectura segura, no sobreescribir memoria en GET |
| AutoPilot | CONFIRMADO | Motor con clasificación, tareas y prompts existente | Reutilizar; no crear un segundo AutoPilot |
| SHARK local optimizado | CONFIRMADO | Evidencia local previa: seis lecturas, cero escrituras, cero llamadas externas | Mostrar la evidencia local con alcance explícito |
| SHARK en producción | NO CERTIFICADO | Sin medición de producción en esta ejecución | Mantener pendiente de certificación |
| Datos deportivos frescos en producción | NO CERTIFICADO | No hay timestamps reales de Render leídos aquí | Mostrar última evidencia local y acción de certificación |
| Falsos live/stale públicos en producción | NO CERTIFICADO | La lógica existe, pero no se ha consultado Render ahora | No declarar cero sin lectura real |
| Telegram operativo en producción | NO CERTIFICADO | Solo se puede comprobar configuración enmascarada local | Dry-run únicamente; nunca enviar |
| Stripe operativo y webhooks | NO CERTIFICADO | El motor puede evaluar presencia/configuración sin llamar a Stripe | Mostrar readiness, no certificar cobros ni webhooks |
| Membresías y precios | REQUIERE REVISIÓN | Catálogo local existe; evidencia comercial/Stripe real no se consulta | Separar catálogo, configuración y transacción probada |
| Exposición de secretos en repo | REQUIERE REVISIÓN | Existen patrones candidatos; todavía no son hallazgos validados | Escanear con redacción y hash parcial, distinguir ejemplos de valores reales |
| Correos o PII en repo | REQUIERE REVISIÓN | Auditoría previa detectó candidatos, muchos en pruebas/evidencias | Clasificar ruta/tipo sin imprimir datos personales |
| RTO/RPO alcanzados | NO CERTIFICADO | No existe simulacro externo completo | Definir objetivos y bloquear nota máxima hasta ensayo |
| Segundo operador | NO CERTIFICADO | Dependencia operativa de una sola persona no está eliminada | Crear runbook ejecutable y criterio de handoff |
| Dead-man externo | NO CERTIFICADO | Sentinel interno no prueba vigilancia desde fuera de Render | Diseñar monitor externo sin activarlo ni crear infraestructura |

## Regla de puntuación

Un sistema no obtiene puntuación máxima por existir en código. Cada score V938 indicará criterios cumplidos, huecos, fuentes y confianza. `NO CERTIFICADO` y `BLOQUEADO POR ACCESO` reducen la confianza, pero no se presentan como averías confirmadas.

## Correcciones locales autorizadas por evidencia

1. Recuperar el módulo compatible de Secret Guard sin duplicar lógica.
2. Añadir el escáner redactor de privacidad/secretos.
3. Endurecer cookies con configuración compatible por entorno.
4. Exigir header en el nuevo Cron V938 y documentar el transporte legacy.
5. Validar firma de Telegram cuando exista secreto configurado y bloquear producción sin él, preservando tests locales.
6. Cerrar conexiones SQLite Data Vault de forma determinista.
7. Crear Operations Center de solo lectura por defecto, con acciones protegidas y sin efectos externos.
