# V939 Memoria de Company Intelligence QA

Destino previsto: `data/runtime/company_intelligence_memory.json`.

- Se crea solo desde POST/Cron autorizado, nunca desde GET.
- Escritura atomica mediante archivo temporal y reemplazo.
- Maximo 30 snapshots y 500 decisiones.
- Tokens, claves, password, cookies, sesiones, email, telefono, IP y tarjetas se redactan.
- Fixture con `api_key` confirma que el valor no persiste y se sustituye por `[REDACTED]`.
- Una aprobacion se registra, pero `automatic_execution=false`.

No se empaqueta memoria dinamica ni PII en el release.
