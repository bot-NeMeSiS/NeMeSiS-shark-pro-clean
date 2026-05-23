# NeMeSiS SHARK PRO V497 — LEGAL DATA INTAKE HUB

Avance centrado en crecer el calendario profundo de Andalucía y fútbol regional siempre dentro de la legalidad.

## Añadido

- Hub legal de fuentes: `/legal-data-hub` y `/fuentes-legales`.
- Política explícita anti scraping ilegal.
- Plantilla CSV descargable: `/api/v497/import-template.csv`.
- Importador legal por CSV: `/api/v497/import-regional-csv`.
- Importador legal por JSON: `/api/v497/import-regional-json`.
- Diagnóstico de cargas y trazabilidad: `/api/v497/legal-diagnostics`.
- Registro persistente de lotes importados en SQLite.
- Validación de provincia, categoría, equipos, competición y fuente permitida.
- Campos de auditoría: source_legal_url, license_notes e integrity_hash.

## Objetivo

Preparar la plataforma para meter calendarios, jornadas y partidos regionales desde:

- carga manual propia verificada;
- fuente oficial/autorizada;
- datasets abiertos con licencia compatible;
- APIs deportivas legales.

## Importante

No hace scraping ilegal. No copia webs privadas. No añade datos protegidos. Solo prepara la entrada legal de información.
