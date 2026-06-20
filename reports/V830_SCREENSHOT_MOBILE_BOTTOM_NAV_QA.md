# V830 Screenshot Mobile Bottom Nav QA

No se generaron screenshots reales desde navegador en esta ejecución, por lo que no se declara pixel-perfect.

La validación se hizo mediante:

- análisis de la captura del usuario;
- inspección del shell real en `templates/base.html`;
- inspección de capas CSS históricas;
- nueva capa CSS V830 final;
- checks automatizados de bottom nav, floating SHARK, overflow, runtime y cobertura de pantallas;
- smoke tests Flask sin 500.

Pendiente recomendado: abrir `/app`, `/partidos`, `/live`, `/picks`, `/shark`, `/profile`, `/telegram` y `/support` en móvil real de 390px/430px y confirmar visualmente que la bottom nav aparece centrada y completa.
