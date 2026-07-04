# QA API preview picks Telegram

Contrato:
- APIs protegidas por sesion admin.
- Sin sesion = 403.
- No secrets.
- No envio real.
- No escritura de cola en dry-run.

Respuesta esperada:
- `would_send`.
- `status`.
- `score`.
- `reasons`.
- `dedupe_key`.
- `membership_variant`.
- `message_preview`.
