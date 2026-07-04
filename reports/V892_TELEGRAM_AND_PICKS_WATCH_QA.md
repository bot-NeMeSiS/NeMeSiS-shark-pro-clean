# V892/V894 Telegram And Picks Watch QA

## Qué vigila

- Telegram configurado sin exponer token.
- No filler.
- Dedupe.
- QUEUE_SKIPPED preservado.
- Picks sin cuota.
- Picks sin seleccion.
- Telegram OK falso.
- Envio real bloqueado por este worker.

## Estado seguro

Si falta dato real, se exige estado como `Sin pick real publicado`, `Cuota pendiente`, `Seleccion pendiente` o `No enviado por seguridad`.
