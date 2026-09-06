# Reglas de Trabajo ChatGPT, Codex y Releases

## Evidencia

- Separar `PRODUCTION`, `LOCAL`, `SIMULATED_TEST` e `INSUFFICIENT_REAL_DATA`.
- No convertir existencia de codigo, asset o test en prueba de experiencia real.
- No ocultar fallos observados; registrar fallo, causa, fix y retest.

## Codigo

- Trabajar solo en la carpeta oficial.
- Leer `REFERENCE_ONLY` solo para imagenes de referencia.
- Cambios pequenos y compatibles con patrones existentes.
- No reescribir `app.py` ni crear engines paralelos sin necesidad demostrada.
- No tocar DB, usuarios, membresias o secretos durante QA.

## Git

- Nunca `git add .`.
- Staging selectivo.
- Sin force push ni reescritura de historia.
- Commit, push y deploy solo con autorizacion expresa.
- Antes de publicar: diff completo, QA y rollback target conocido.

## Produccion

- Observar auto-deploy; no lanzar deploy duplicado.
- Alinear Local == origin/main == Render por SHA.
- Production Sentinel despues de cada release.
- Rollback recomendado ante regresion P0; nunca maquillar evidencia.

## Datos externos y dinero

- No llamadas adicionales a proveedor para observar si DB/cache/logs bastan.
- No proveedor nuevo ni aumento de plan sin aprobacion.
- Telegram real y Stripe live requieren autorizacion explicita.
- Nunca exponer secretos en chat, URL, query, logs, informes o capturas.

