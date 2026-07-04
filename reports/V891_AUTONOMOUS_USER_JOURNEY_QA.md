# V891/V893 Autonomous User Journey QA

## Alcance

El motor `sentinel_user_journey_engine.py` revisa rutas de cliente y admin con `Flask.test_client`, sin navegador real y sin acciones destructivas.

## Rutas cliente auditadas

- `/`
- `/cliente-login`
- `/registro`
- `/app`
- `/inicio`
- `/panel-cliente`
- `/partidos`
- `/calendar`
- `/live`
- `/directo`
- `/picks`
- `/shark`
- `/telegram`
- `/profile`
- `/support`
- `/track-record`
- `/memberships`

## Rutas admin auditadas

- `/admin/dashboard`
- `/admin/company-os`
- `/admin/company-audit`
- `/admin/continuous-sentinel`
- `/admin/sentinel-workflow`
- `/admin/sentinel-issues`
- `/admin/autonomous-sentinel`
- `/admin/visual-worker`
- `/admin/payments`
- `/admin/memberships`
- `/admin/users`

## Señales revisadas

- 500/502.
- 404 en rutas clave.
- enlaces vacios o peligrosos visibles.
- mojibake.
- `None`, `null`, `undefined` visibles.
- navegación cliente dentro de admin.
- promesas de apuestas garantizadas.

## Limitacion honesta

No se declara pixel-perfect porque este worker no ejecuta capturas reales de navegador.
