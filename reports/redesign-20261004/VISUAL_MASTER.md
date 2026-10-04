# NeMeSiS — Visual Master de la rama

La dirección acordada es Dark Premium. Las maquetas históricas sirven para estructura e identidad; el encargo actual sustituye su LIVE verde y su fondo oceánico dominante.

| Área | Regla implementada | Propietario |
|---|---|---|
| Core | Fondo #080b12, superficie #141c29, superficie elevada #1b2636, radio 14 px; texto claro y jerarquía tipográfica | design-tokens.css |
| Compatibilidad | 200 variables históricas apuntan al Core; las hojas históricas están retiradas del build y de las plantillas | visual_css_origins.json |
| Shell cliente | Cinco destinos principales; cabecera PC, cuenta desplegable y navegación inferior móvil | v933_navigation.html / base.html |
| Deporte | Equipos y marcador protagonistas; hora de Madrid, estado canónico, competición, favoritos y acceso al partido | v933_ui.html / v944_match_center.html |
| LIVE | Rojo para directo confirmado; resumen neutro sin actividad. Ninguna modificación de Sports Truth | componentes deportivos |
| SHARK | Violeta en acciones y verde/violeta en inteligencia; explicaciones sin detalles del modelo o infraestructura | shark.html / platform-help.css |
| Membresías | FREE, PRO y ELITE según permisos reales; precios y límites existentes, sin ventajas inventadas | membership.html |
| Cuenta | Perfil, servicios, renovación, actividad y seguridad con componentes canónicos | account_center.html |
| Estados | Vacío, carga, error y datos limitados con explicación y siguiente paso; diagnósticos restringidos a admin | client_message / state_notice |
| Identidades | Asset oficial o ya cacheado; iniciales estilizadas si falta o falla. Sin escudos inventados | team_logo / v937-product-client.js |
| Founder | Recomendaciones antes de métricas/chat; telemetría e histórico secundarios; aplicar operaciones sin énfasis primario | admin_dashboard.html |
| Móvil | Adaptación a 320, 390, 768 y 1024 px; controles agrupados y navegación táctil; carruseles contenidos sin desbordar la página | design-system.css |

Los dos archivos globales son las fuentes editables. product-system.css es exclusivamente el resultado verificado de su compilación. Las hojas por función (constructor, ayuda y Founder) consumen el Core y conservan sus reglas de interacción. No se añade otra hoja global de overrides.

Las capturas finales prueban la implementación en Chromium con datos reales cacheados y estados sin contenido donde la captura no aporta datos. No se afirma coincidencia exacta de píxeles con una referencia ni certificación de todos los navegadores físicos.

Master Finalization Program sigue BLOQUEADO por certificación de almacenamiento pendiente. Esta revisión no cambia DB_PATH, secretos, persistencia o el mecanismo de certificación.
