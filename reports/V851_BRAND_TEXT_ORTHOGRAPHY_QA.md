# V851 Ortografía de Branding

## Problema confirmado
- `templates/home.html` contenía `EspaÁa/Madrid`.

## Corrección
- `Panel cliente · datos reales · Hora España/Madrid`.
- `Hora España/Madrid`.

## Revisión automática
El check `tools/check_v851_brand_text_orthography.py` revisa templates principales para:
- `ESPAÃ`
- `EspaÁa`
- `Ã`
- `Â`
- `�`
- términos sin acento como `proximo`, `analisis`, `competicion`, `informacion`, `conexion`, `membresia`, `pais`, `senales`

## Resultado
Los textos de branding revisados quedan en español correcto y sin mojibake visible objetivo.
