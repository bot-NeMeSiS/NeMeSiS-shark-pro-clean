# V784 Smoke / Preflight Validation Foundation

Versión: `V784_SMOKE_PREFLIGHT_VALIDATION_FOUNDATION`

## Por qué existe esta versión

Hasta ahora el ZIP podía pasar checks estáticos, compilación Python, Jinja parse y auditoría ZIP, pero si el entorno donde se generaba el paquete no tenía Flask instalado no se podía ejecutar un smoke Flask real con `app.test_client()`.

Eso no significa que Render vaya a fallar, pero sí significa que faltaba una capa de verificación más fuerte antes de desplegar.

## Qué añade

- `tools/smoke_flask_real_routes.py`: smoke Flask real con DB temporal, import de la app y pruebas sobre rutas críticas.
- `tools/render_preflight_check.py`: comprobación remota contra Render después del deploy, sin necesitar Flask local.
- `tools/check_v784_smoke_preflight_validation.py`: auditoría estática de esta nueva capa.
- Reportes generados en `reports/`.

## Qué comprueba el smoke Flask real

- Dependencias instaladas: Flask, Werkzeug, Jinja2 y Stripe.
- Importación real de `app.py`.
- Rutas públicas principales.
- Rutas cliente que pueden redirigir si no hay sesión.
- Rutas admin que pueden redirigir si no hay login.
- Rutas Stripe POST que no deben devolver 500 aunque rechacen por CSRF/config.
- Live/API básicas sin depender de APIs reales.

## Cómo usarlo localmente

```bash
python -m pip install -r requirements.txt
python tools/smoke_flask_real_routes.py
```

Para JSON completo:

```bash
python tools/smoke_flask_real_routes.py --json
```

## Cómo usarlo después de desplegar en Render

```bash
python tools/render_preflight_check.py https://bot-apuestas-crgf.onrender.com
```

## Qué mejora

- Detecta errores 500 antes de que los vea un cliente.
- Detecta importaciones rotas.
- Detecta templates que explotan en runtime.
- Detecta problemas en rutas de pagos, live, cliente y admin-login.
- Separa claramente el problema de dependencias locales del funcionamiento real en Render.

## Qué no toca

- no toca Telegram
- no toca Cron
- no toca `DB_PATH`
- no toca usuarios, sesiones ni membresías
- no toca Stripe V782 salvo validarlo
- no toca live V780
- no toca escudos V779
- no toca Madrid Time engine

## Resultado esperado

Desde esta versión, cuando alguien tenga el entorno instalado correctamente, podrá validar la app de forma más real con Flask antes de subirla. Y después de subirla, podrá lanzar un preflight remoto contra Render para comprobar que las rutas principales no devuelven 500.

Nota literal: preflight Render incluido para comprobación remota.
