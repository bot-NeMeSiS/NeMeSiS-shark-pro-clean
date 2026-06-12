# V717_1_TELEGRAM_PREMIUM_MESSAGE_ENGINE

## Objetivo
Mejorar de forma específica la experiencia de Telegram de NeMeSiS SHARK PRO sin rehacer la app ni tocar la base estable de Render/Cron.

## Cambios principales
- Nuevo formato de mensajes Telegram más profesional, corto y comercial.
- Picks premium con estructura clara: competición, hora España, partido, pick, mercado, cuota, stake, confianza, riesgo, value, motivo y precaución.
- Resumen diario Telegram menos técnico y más útil.
- Alertas live con mejor jerarquía visual.
- Filtros reforzados para no enviar como premium picks con cuota pendiente, sin cuota real, sin mercado, antiguos, finalizados o con textos tipo None/null/undefined.
- Botones inline mejorados: abrir análisis, ver picks y directo SHARK cuando proceda.
- Respuesta pública de Cron compacta: el detalle largo queda guardado para diagnóstico admin interno.
- Motor autónomo de Telegram actualizado con mensajes más claros y responsables.
- `.gitignore` reforzado para evitar cachés, entornos virtuales, bases locales, logs, backups y ZIPs.

## Archivos principales tocados
- `app.py`
- `VERSION.txt`
- `engines/telegram_delivery_engine.py`
- `engines/telegram_autonomous_delivery_engine.py`
- `requirements-dev.txt`
- `.gitignore`

## Validación realizada en este entorno
- `python -m py_compile app.py`: OK
- `python -m py_compile engines/telegram_delivery_engine.py`: OK
- `python -m py_compile engines/telegram_autonomous_delivery_engine.py`: OK
- `python -m compileall -q .`: OK
- Prueba directa de formateadores Telegram con pick realista: OK

## Limitación del entorno
No se pudo ejecutar `tools/smoke_check.py` ni rutas Flask porque este entorno no tiene Flask instalado. El proyecto conserva `requirements.txt` con Flask y `pytest`, por lo que en entorno Render/local con dependencias instaladas debe validarse con:

```bash
pip install -r requirements.txt
python tools/smoke_check.py
pytest -q
```

## Cómo probar en Render
1. Subir el ZIP Render Ready.
2. Verificar `/api/runtime-version`.
3. Probar `/api/automation/telegram/tick?secret=SECRET_OCULTO`.
4. Probar `/api/automation/daily/run?secret=SECRET_OCULTO`.
5. Confirmar que el JSON de Cron es compacto.
6. Revisar `/admin/telegram/diagnostics` para el detalle largo.
7. Confirmar en Telegram que los mensajes ya salen como tarjetas premium.

## Pendiente dependiente de producción
- Comprobar envío real con bot/canal activo.
- Validar escudos/logos reales según datos disponibles de APIs.
- Ajustar límites de mensajes según comportamiento real del canal.
