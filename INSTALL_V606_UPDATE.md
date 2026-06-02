# Instalación V606 — Blueprint Migration Phase 1

Esta actualización es **segura y no invasiva**.

## Cómo instalar

1. Descomprime este ZIP.
2. Copia estas carpetas sobre tu carpeta actual de NeMeSiS SHARK PRO:
   - `engines/`
   - `blueprints/`
   - `tools/`
   - `tests/`
3. No borres nada de tu app actual.
4. Ejecuta si quieres generar el mapa de rutas:

```bash
python tools/route_map_v606.py
```

## Qué hace

- No mueve rutas todavía.
- No cambia login.
- No cambia Telegram.
- No cambia picks.
- No cambia Render.
- Prepara la migración ordenada de `app.py` a Blueprints.
- Añade una herramienta para auditar y agrupar rutas.

## Siguiente paso recomendado

V607 debería migrar primero rutas de autenticación a Blueprint, pero solo cuando V606 haya generado el mapa de rutas y confirmado que no hay conflictos.
