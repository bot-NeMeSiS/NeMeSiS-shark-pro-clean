# V933 Public UI QA

## Pantallas

- `/`
- `/cliente-login`
- `/registro`
- `/support`

## Resultado

La home usa un unico hero, marca visible, CTA principal azul, acceso secundario, resumen `Hoy en NeMeSiS`, producto, planes, confianza y juego responsable. El resumen deportivo comparte el mismo filtro de validez que la lista visible y separa registros incompletos.

Login y registro usan el shell publico canonico, formularios legibles, acciones inequívocas y copy comercial responsable. No muestran navegacion admin, datos tecnicos ni cifras de referencia.

## Responsive

Las cuatro rutas se capturaron en siete viewports. No hubo overflow, errores HTTP ni textos de formulario cortados. En movil se oculta la navegacion desktop y las acciones mantienen tamano tactil.

## Estado

- Hero duplicado: no
- Datos inventados: no
- CSS cache busting: activo con V933
- Service worker: `NEMESIS_CACHE_V933`
- Revision humana pixel-perfect: pendiente

