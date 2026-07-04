# V892 Render Runtime Alignment QA

Consulta real: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado:

- Produccion Render sirve: `V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL`.
- Local sirve: `V892_SENTINEL_ISSUES_COMMAND_CENTER_COPY_FIX_PROMPTS_FINAL`.
- `app_py_path` en Render: `/opt/render/project/src/app.py`.
- `db_path` en Render: `/data/database.db`.
- `openai_configured`: `false`.
- `telegram_configured`: `true`.
- `api_sports_configured`: `true`.
- `the_odds_configured`: `true`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `last_error_state`: historico saneado para `Invalid header value`.

Conclusion:

Render no esta alineado con el workspace local. No se declara V892 desplegada. La version queda preparada localmente y requiere push/deploy manual correcto para que produccion muestre V892.

Siguiente accion:

1. Subir el contenido raiz local a GitHub.
2. Confirmar `VERSION.txt` y `app.py` en GitHub con V892.
3. Ejecutar en Render `Clear build cache & deploy`.
4. Volver a consultar `/api/runtime-version`.
