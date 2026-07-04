# V890 QA DB_PATH local

Hallazgo:
- En checks/smoke locales sin `DB_PATH`, la app intentaba inicializar `/data`.
- En Windows local eso genera `WinError 5 Acceso denegado`.

Solucion:
- Nuevo helper `resolve_default_db_path()`.
- Si `DB_PATH` existe, se respeta.
- Si Render esta presente, fallback `/data/database.db`.
- Si es local, fallback `data/database.db`.

Impacto:
- Mejora smoke local y checks sin tocar la configuracion real de Render.
