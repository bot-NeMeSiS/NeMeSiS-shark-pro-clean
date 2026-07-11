# V930 Component Consistency QA

- 23 componentes canónicos declarados y usados.
- 26 templates reales importan `components/v930_ui.html`.
- Shells: público, cliente desktop, cliente móvil y admin.
- Componentes: headers, KPIs, botones, chips, empty states, tablas, filtros, match/live/pick/plan/profile cards, provider state y logo fallback.
- Navegación V929 preservada; `/clientes` y sus aliases siguen bajo el motor de integridad.
- Iconos V930 se hidratan desde `static/v930-icons.js`, sin CDN ni llamada externa.
- Semántica: azul para acción, cian para inteligencia/Telegram, verde para estado positivo, amarillo para atención, rojo para error y dorado para ELITE.
- Cards limitadas a radio de 8 px y controles táctiles estables.

El check automático `check_v930_component_consistency.py` pasa sin findings.
