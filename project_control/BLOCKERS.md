# Blockers

Actualizado 2026-09-20. Condiciones transversales, no otra cola.

<!-- blockers:start -->
| ID | Motivo | Desbloqueo |
|---|---|---|
| ART | H07/R9 y conformidad global no certificados | Comparacion concreta con referencias y evidencia visual del main actual |
| EXTERNAL | Cobertura, derechos, proveedor profundo y frescura no plenamente certificados | Muestra real fechada y permitida; nunca sustituir con fixture |
| PUBLISH | El main actual ya fue publicado; futuros cambios requieren gate nuevo | PR sobre main + CI del SHA exacto + autorizacion de merge + verificacion Render |
| COMMERCIAL | Pagos externos/renovacion y ELITE+ no certificados | Validar catalogo y recorridos bajo autorizacion sin inventar cobros |
| ENV | Positivos SE-01/bloqueos ambientales historicos no recertificados | Reproducir solo donde sea necesario sin rebajar seguridad |
| LEGACY | No todos los consumidores/prescindibilidad estan demostrados | Cero consumidores + alternativa + pruebas + rollback antes de retirar |
| MATERIAL | Material historico no disponible no se infiere por nombre | Aportar solo material concreto cuando sea imprescindible |
<!-- blockers:end -->

## Bloqueos concretos vigentes

- API-Football deep/provider: ultima evidencia persistida PARTIAL / ACCESS_FAILED; freshness profunda NOT_ESTABLISHED.
- `/app`: rendimiento productivo requiere nueva medicion; no ampliar timeout para ocultarlo.
- Directos: codigo integrado, pero feed real universal y hardware fisico no certificados.
- Stripe/pagos externos: NOT_CERTIFIED.
- Design: R9/H07 y conformidad global pendientes.
