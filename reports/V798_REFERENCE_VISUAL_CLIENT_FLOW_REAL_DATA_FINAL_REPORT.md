# V798_REFERENCE_VISUAL_CLIENT_FLOW_REAL_DATA_FINAL

## Objetivo
Avance visual cliente basado en las imágenes de referencia subidas, manteniendo la regla comercial principal: datos reales siempre y estados vacíos elegantes cuando no exista información sincronizada.

## Cambios principales
- Nueva capa visual premium V798 en cliente: fondo oscuro, profundidad, rail lateral PC, cards móviles y marca NeMeSiS SHARK PRO más cercana a la referencia.
- Rework de `/app`, calendario/partidos, directo, picks, detalle de partido, cuenta y Telegram cliente.
- Botón `Cerrar sesión` visible y útil en la experiencia de cuenta y navegación existente.
- Cards de partido/pick/directo enlazadas a detalle real, SHARK o pantalla relacionada.
- Detalle de partido reforzado con datos disponibles reales y sin formas/porcentajes inventados.
- Cuenta cliente muestra actividad real registrada; si no existe, muestra estado vacío sin ejemplos ficticios.
- Telegram cliente y Command Center dejan de mostrar números/preview ficticios: solo datos reales o estados pendientes.

## Protección de producto
No se han tocado `DB_PATH`, secretos, usuarios, sesiones, pagos, membresías, Madrid Time, Telegram real, Render Cron ni la lógica crítica de picks/resultados. No se inventan partidos, cuotas, resultados, ROI ni métricas.

## Validación local
- `python3 -m py_compile app.py`
- Parse Jinja de plantillas críticas V798
- `tools/check_v798_reference_visual_client_flow_real_data.py`
- Build limpio y audit ZIP Render Ready previstos en esta release.

## Pendiente en Render
Validar con datos reales de producción: partidos sincronizados, picks activos, directos, Telegram real y navegación en móvil/PC con sesión cliente real.
