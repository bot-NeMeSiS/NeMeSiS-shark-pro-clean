# V837 Ecosystem Linking Final QA

## Cliente

- `/app` enlaza con partidos, live, picks, SHARK, perfil, Telegram y soporte.
- Partidos enlazan con detalle.
- Picks enlazan con partido y SHARK.
- SHARK enlaza con picks, combis, Telegram, live y soporte.
- Profile enlaza con Telegram, soporte, favoritos, histórico y logout.
- Telegram enlaza con soporte/perfil.

## Admin

- Admin enlaza dashboard, automatización, Telegram, data center, usuarios, membresías, pagos, health/runtime y vista cliente.

## Verificación

Se crea `tools/check_v837_ecosystem_linking.py`.
