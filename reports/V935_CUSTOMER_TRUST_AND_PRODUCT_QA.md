# V935 Customer Trust And Product QA

Cliente muestra un contrato compacto y comprensible en dashboard, picks, historico, SHARK y detalle de partido:

- procedencia cuando existe;
- frescura de dato/cuota;
- picks completos;
- historico solo evaluable;
- ausencia de beneficio garantizado;
- estado seguro cuando no hay sincronizacion.

SHARK explica limites y el motivo `No publicar` si no existe una seleccion completa con cuota, fuente y hora vigentes. Telegram queda preparado, no enviado. Personalizacion y onboarding se mantienen disponibles sobre favoritos y cuenta reales; no se inventan preferencias.

Las pruebas cliente confirmaron 200 en `/app`, `/picks`, `/track-record` y `/shark`, panel visible y ausencia de `DB_PATH`, secretos, excepciones del proveedor o diagnosticos internos.
