# V873 visual producción real QA

## Intento de captura

El entorno de navegador/Playwright no está disponible sin permisos adicionales. En V872 ya devolvió `EPERM` al resolver el runtime Node.

## Qué se pudo probar en real

- Runtime de producción Render.
- Versión de producción V871.
- Configuración real de provider, Telegram, OpenAI y logos.

## Qué no se declara

- No se declara pixel-perfect.
- No se declara captura visual V873.
- No se declara producción V873.

## QA estático aplicado

- CSS V873 refuerza fallback logos.
- CSS V873 mantiene admin sin nav/widget cliente.
- SHARK comunica modo seguro si OpenAI no está configurado.
- Runtime local queda preparado para explicar estados reales.
