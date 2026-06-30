# V871 Real Progress Visibility Audit

## Causas detectadas
- CSS V870 sí se cargaba, pero algunos defectos estaban en templates y JS base.
- El cache busting cambia ahora a V871.
- Varias mejoras estaban en macros, pero las macros tenían mojibake en defaults.
- La navegación lateral repetía label + label, reduciendo percepción premium.
- JavaScript con ternarias dañadas podía romper comportamientos que hacen que la UI se sienta viva.

## Correcciones V871
- Cache CSS V871.
- `data-v871-shell`.
- CSS V871 pequeño para acciones limpias.
- Macros saneadas.
- Nav cliente/admin saneada.
- Sentinel reforzado para detectar defectos similares.
