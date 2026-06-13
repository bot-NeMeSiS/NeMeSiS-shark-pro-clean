# V767 Madrid Time QA Checklist

- [x] `VERSION.txt` en V767.
- [x] `APP_VERSION` en V767.
- [x] Timestamps UTC con `Z` se convierten a Europe/Madrid.
- [x] Timestamps con offset se respetan y se muestran en Europe/Madrid.
- [x] Valores manuales `match_date + kickoff_time` se tratan como Madrid local.
- [x] Cliente no ve campos crudos de fecha/hora.
- [x] Admin no ve campos crudos cuando hay filtro Madrid disponible.
- [x] Telegram conserva formato Madrid.
- [x] Checks V760-V766 compatibles.
- [x] Nuevo `tools/check_v767_madrid_time_everywhere.py`.
