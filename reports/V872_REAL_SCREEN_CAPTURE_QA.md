# V872 capturas reales PC/móvil

## Intento de captura

Se intentó habilitar Playwright desde el runtime Node disponible para capturar pantallas reales. El entorno devolvió:

`EPERM: operation not permitted, lstat 'C:\Users\aloha\AppData\Local\OpenAI\Codex'`

No se fuerza escalado ni se abre navegador GUI sin autorización. Por tanto:

- No se declara pixel-perfect.
- No se declara certificación visual por captura nueva V872.
- Se conserva la evidencia V871 existente en `reports/V871_*.png`.
- La revisión real de Render de V872 queda pendiente de deploy manual + navegador autorizado.

## Validación alternativa

Se usa runtime real de Render para confirmar versión/configuración y se hacen checks HTML/CSS/Jinja locales. Las correcciones V872 son defensivas y acotadas a defectos detectables sin captura nueva:

- overflow horizontal móvil;
- acciones y CTAs con ancho excesivo;
- estados vacíos sobredimensionados;
- nav/widgets de cliente ocultos en admin;
- saneado de `last_error` de runtime.
