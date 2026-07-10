# V929 Click Browser QA

- Motor: Playwright Chromium real.
- Base: servidor Flask local con DB temporal.
- Sesiones: publico, cliente mock, admin mock.
- Clics probados: `245`.
- Clics correctos: `245`.
- Fallos: `0`.
- Acciones peligrosas: `false`.
- APIs externas: deshabilitadas en el runner.
- Logout, pagos, envios, sync y endpoints API: excluidos por seguridad.
- Capturas de fallo: `reports/V929_browser_qa_navigation/failures/`.
- No se declara pixel-perfect; este QA certifica navegacion, no equivalencia visual exacta.
