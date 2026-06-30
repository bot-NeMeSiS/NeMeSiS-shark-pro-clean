# V866 mobile visual QA

## Objetivo
Validar y endurecer móvil sin una feature grande.

## Cambios seguros
- Se añadió capa CSS V866 con guard global de `overflow-x`.
- Se protegieron `pre`, `code`, tablas, cards, prompts, rutas y bloques de workflow para que no rompan ancho móvil.
- Se ajustó bottom nav móvil para respetar ancho de viewport y safe-area.

## Capturas reales
Ejecutadas con servidor local aislado, DB temporal y viewport 390x844.

| Ruta solicitada | Ruta final | Scroll horizontal | Captura |
| --- | --- | --- | --- |
| `/` | `/` | No | `reports/V866_mobile_home.png` |
| `/app` | `/cliente-login` | No | `reports/V866_mobile_app.png` |
| `/picks` | `/picks` | No | `reports/V866_mobile_picks.png` |
| `/live` | `/live` | No | `reports/V866_mobile_live.png` |
| `/shark` | `/shark` | No | `reports/V866_mobile_shark.png` |

Nota: `/app` redirigió a login porque la prueba se hizo sin sesión real. No se usaron credenciales ni se transmitieron datos.

## Validación estática
Sentinel estático V866 completado con score 10.0 y sin issues abiertos. Esta validación no sustituye screenshots reales.

## Métrica de viewport
En todas las rutas medidas, `documentElement.scrollWidth` fue menor o igual que `window.innerWidth`; no se detectó scroll horizontal.

## Resultado esperado
- Sin scroll horizontal por textos largos.
- Admin Sentinel más compacto.
- Errores/prompts largos no rompen el layout.
