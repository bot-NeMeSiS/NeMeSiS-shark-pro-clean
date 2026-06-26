# V851 Logo, Marca y Header - Auditoría

## Base real
- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- Base confirmada: `V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL`
- ZIP antiguo V827: no usado como base.

## Hallazgos
- El header superior usaba una marca escrita directamente en `templates/base.html`, separando icono y texto de forma poco controlada.
- El rail cliente y el rail admin repetían estructuras propias de logo, lo que podía producir tamaños y alineaciones distintas entre móvil, PC y admin.
- En la pantalla home había texto roto: `EspaÁa/Madrid`.
- El favicon apunta al SVG ligero `static/img/shark-logo.svg`; no se detectó `static/manifest.json`.

## Corrección aplicada
- Se creó `templates/partials/brand_logo.html` con un componente reutilizable `nemesis_brand`.
- Topbar, rail cliente y rail admin usan la misma marca: icono SHARK + `NeMeSiS` + `SHARK PRO`.
- Se preservaron clases antiguas (`brand`, `v828-rail-brand`, `v808-admin-rail-brand`) para no romper estilos previos.
- Se añadió el bloque CSS V851 para proporciones, alineación y responsive.
- Se corrigió `Hora España/Madrid`.

## Resultado esperado
La marca deja de verse como icono aislado y pasa a leerse como identidad premium completa en móvil y PC.
