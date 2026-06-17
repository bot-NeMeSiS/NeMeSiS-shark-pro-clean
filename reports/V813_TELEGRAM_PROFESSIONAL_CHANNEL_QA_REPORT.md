# V813 Telegram Professional Channel QA Report

## Objetivo

Mantener la app amplia, pero proteger el canal Telegram automático para que no parezca un feed de ligas irrelevantes o no profesionales.

## Cambios

- Se añadió modo estricto `TELEGRAM_PRO_CHANNEL_STRICT`, activo por defecto.
- Se bloquean competiciones juveniles, reservas, filiales, amistosos menores, regionales, RFEF/lower tiers y deportes no fútbol.
- Se mantienen competiciones top: LaLiga, Segunda, Premier, Championship, Serie A/B, Bundesliga, Ligue 1/2, Primeira, Champions, Europa, Conference, Copa, FA Cup, Mundial, Euro, Nations League, Libertadores, Sudamericana, MLS y Eredivisie.

## Resultado esperado

- El canal automático prioriza picks de valor comercial.
- La app interna puede seguir mostrando cobertura amplia.
- El envío manual no se rompe.

## Validación automatizada

`tools/check_v813_full_ecosystem_restructure.py` comprueba:

- NBA bloqueada.
- Regional bloqueado.
- Juveniles bloqueados.
- Champions permitida.
