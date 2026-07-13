# V937 Next Steps

## Accion inmediata

1. Damian revisa las capturas clave de home, cliente, calendario/live/picks, SHARK, Telegram y command centers admin.
2. Autorizar merge/push/deploy solo si la revision humana acepta la jerarquia y el copy.
3. Desplegar el contenido interno de `release_output/V937_DEPLOY_ROOT_CONTENTS`.
4. Confirmar que desaparece el `FileNotFoundError` controlado que hoy presenta el runtime V936.
5. Confirmar runtime V937, archivos alineados, cache V937, Sentinel 0 y home limpia.

## Proximas dos semanas

- Ejecutar QA autenticado real en Render sin conservar credenciales ni cookies.
- Observar cobertura, frescura y descartes del dato deportivo real.
- Medir activacion por ruta: calendario, picks, SHARK, Telegram y membresias.
- Revisar soporte, abandonos y comprension del Indice de Confianza.
- Cerrar solo regresiones demostradas; no abrir una nueva reconstruccion visual.

## Condicion de salida

V937 pasa de candidata a produccion unicamente cuando Render devuelva la version exacta, archivos alineados y no existan regresiones reales en los flujos autenticados.
