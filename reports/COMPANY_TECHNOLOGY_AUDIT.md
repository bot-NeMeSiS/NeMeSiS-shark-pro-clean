# NeMeSiS SHARK PRO - Auditoría tecnológica

## Arquitectura observada

```text
Navegador/PWA
  -> Render Web Service (Gunicorn, 1 worker gthread, 3 threads)
     -> Flask app (`app.py`, monolito)
        -> rutas públicas / cliente / admin / API / cron
        -> templates Jinja + CSS/JS + service worker
        -> servicios y engines
           -> SQLite (`DB_PATH=/data/database.db` en Render)
           -> caché persistente/local
           -> proveedor(es) deportivos y cuotas
           -> SHARK/OpenAI si está configurado
           -> Telegram
           -> Stripe/webhooks
        -> auditoría, Sentinel, Navigation Integrity, Browser QA
  -> Render Cron (sports sync cada 15 minutos según blueprint)
GitHub main
  -> GitHub Actions
  -> Render Auto-Deploy / workflow de despliegue
  -> runtime/version/SHA health
```

## Inventario técnico

| Área | Evidencia | Evaluación |
|---|---|---|
| Núcleo | `app.py` de ~1.2 MB | Funcional, alto acoplamiento y gran blast radius. |
| Rutas | 664 reglas; 625 GET únicas | Cobertura enorme; una duplicidad exacta confirmada. |
| Templates | 182 parseadas; 135 referenciadas estáticamente | Sin includes faltantes observados. |
| Frontend | CSS/JS propios, PWA, 16 referencias | Identidad coherente; deuda CSS histórica elevada. |
| DB | SQLite, compatibilidad legacy y locks | Adecuada para beta pequeña; no para escala sin medición. |
| Caché | persistente/local y políticas de frescura | Buena base, telemetría real incompleta. |
| Automatización | cron deportivo, master tick, workforce | Mucho código; solo un cron está demostrado en blueprint. |
| CI | compile, checks, smoke, release | Estado oficial divergente y Secret Guard roto. |
| Release | ZIP/deploy root/version flags | Trazabilidad fuerte, volumen excesivo de artefactos. |
| Observabilidad | Sentinel, health, logs en DB, runtime | Amplia localmente; falta monitor externo y alerta humana. |

## Datos y persistencia

- `DB_PATH` de Render apunta a `/data/database.db`.
- El snapshot local pasa `PRAGMA integrity_check`.
- Pruebas V931/V932 cubren DB moderna, legacy, vacía y bloqueada.
- El modo bloqueado se recupera sin 500, pero tarda alrededor de 1.8 s en el test.
- No se probó persistencia tras restart/redeploy en esta auditoría.
- Backups y DB parecen compartir el mismo disco, por lo que no son recuperación ante pérdida del volumen.
- Data Vault valida SHA, pero la prueba temporal detectó una conexión no cerrada.

## Integraciones

### Datos deportivos

El render de páginas está diseñado para no llamar proveedores directamente. Usa DB/caché y separa completos, stale e incompletos. Los checks actuales validan que un live necesita marcador, minuto o fase real y frescura válida. Esto está confirmado localmente, no en la alimentación real actual.

### Telegram

Existen cola, dedupe, límites y dry-run. El webhook entrante no demuestra autenticación de origen. No se certificó entrega real.

### Stripe

El webhook verifica firma e idempotencia y el motor aplica downgrade seguro. No se certificaron catálogo, portal, checkout ni webhook de producción.

### SHARK

El candidato local reduce el trabajo de GET a 6 lecturas, 0 escrituras y 0 red. La lógica de modo seguro evita conclusiones sin contexto. No está confirmado en `main`/Render.

## GitHub y Render

- El repositorio es público y contiene 8,850 archivos tracked.
- 2,017 archivos bajo `.venv` están tracked pese al `.gitignore` actual.
- `reports/` ocupa aproximadamente 1.6 GB y contiene miles de artefactos/capturas.
- `render.yaml` fija Python 3.11.9; workflows usan mezcla 3.11/3.12.
- El workflow de deploy de `main` local es manual y no instala dependencias antes de import; PR #1 propone la corrección, pero no está integrado según la evidencia de corte.
- No se pudo certificar SHA/runtime en Render desde este entorno.

## Deuda tecnológica priorizada

1. Restaurar Secret Guard y reproducibilidad de CI.
2. Cerrar autenticación de webhooks/cron y cookies.
3. Implementar backup off-site y restore drill.
4. Instrumentar producción desde fuera de Render.
5. Resolver ruta duplicada y tests obsoletos.
6. Extraer dominios del monolito de forma incremental.
7. Definir umbral de migración SQLite a Postgres.
8. Reducir artefactos tracked tras clasificación segura.

## Diagrama de recuperación

```text
Monitor externo detecta degradación
  -> Incident Commander confirma runtime/SHA/health
  -> activa modo degradado o mantenimiento
  -> conserva DB y disco
  -> contiene proveedor/Telegram/Stripe mediante kill switch
  -> rollback de código a SHA conocido si aplica
  -> restauración de DB solo con backup validado y aprobación doble
  -> smoke público + autenticado + datos + pagos en test
  -> observación y cierre con evidencia
```

