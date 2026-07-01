# V881 Sentinel Nav Duplication Rules QA

## Reglas añadidas

`V881_NAV_DUPLICATION_RULES` detecta:

- sidebar duplicado;
- href repetido en la misma zona;
- label repetido en la misma zona;
- nav cliente en admin;
- nav admin en cliente;
- bottom nav en admin;
- floating SHARK en admin;
- command strip duplicado;
- client rail legacy renderizado;
- labels duplicados como `SHARK SHARK` y `Telegram Telegram`.

## Objetivo

Si el problema vuelve, Sentinel no debe tratarlo como OK silencioso.
