# V937 Render Deployment Certification

## Resultado

**PASS tecnico de despliegue.** No equivale a autorizacion de lanzamiento.

- Runtime anterior: V936 con FileNotFoundError controlado.
- Candidate: `2500491262a8bbe246823163f1e361b008bc21d7`.
- Merge candidato a main: `aa66ee28929861a45114a0cc3725d8292e3c406f`.
- Hotfix: `90e5935`.
- Main final y origin/main: `0cc17b323b5508fe9de7905f3a1307e71deffdc7`.
- Runtime observado: V937 exacta, `version_files_match=true`, `deployment_alignment_status=aligned_local_files`.
- Commit observado por runtime: `0cc17b323b5508fe9de7905f3a1307e71deffdc7`.
- CSS: cache busting activo; hash publico `119c6481e28d9cba`.
- Service worker: `NEMESIS_CACHE_V937`, sin cache obsoleta de HTML/CSS.
- Health: HTTP 200, DB configurada e inicializada.
- Deploy ID y logs privados de Render: no disponibles en esta sesion; no se inventan.

## Hotfix aplicado

La regla `.gitignore` `*token*` excluia `static/v933_design_tokens.css` del commit aunque el archivo existia localmente y en releases anteriores. Render no podia leerlo al construir `/api/runtime-version`. El hotfix rastrea explicitamente ese CSS, protege su lectura en runtime y anade una regresion al check V937. Un archivo Git limpio reprodujo y despues confirmo la correccion.

## Estabilidad

La identidad V937 se confirmo inmediatamente, despues de mas de cinco minutos y de nuevo a las 09:29 Madrid. No reaparecio el FileNotFoundError.
