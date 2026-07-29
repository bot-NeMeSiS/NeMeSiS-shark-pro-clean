# Auditoría UX Copy

Estado: PASS LOCAL
Producción modificada: false

## Método

Se revisaron plantillas, rutas principales, muestras Browser QA y textos visibles en cliente y administración. La revisión se centró en calidad editorial, coherencia terminológica, ausencia de mojibake y comprensión comercial.

## Cobertura revisada

- 194 plantillas Jinja parseadas.
- 72 comprobaciones Browser QA en 24 escenarios y 3 viewports.
- Cliente: landing, app, calendario, directo, picks, track record, Telegram, membresías, perfil, favoritos, SHARK y centros deportivos.
- Admin: dashboard, centro de desarrollo, panel de empresa, centro de operaciones, Sentinel AutoPilot y configuración.
- Código de apoyo con textos visibles en `app.py` y motores administrativos.

## Hallazgos corregidos

### Mojibake y caracteres rotos

Se corrigieron textos con codificación dañada o signos de interrogación en palabras españolas. Ejemplos de familias corregidas:

- próximo / próximos
- configuración
- sincronización
- revisión
- histórico
- metodología
- membresía
- vinculación
- diagnóstico
- navegación
- contraseña
- señal

### Inglés residual innecesario

Se sustituyeron etiquetas visibles mezcladas con inglés por castellano consistente:

- Centros deportivos.
- Sistemas de inteligencia.
- Paneles de administración.
- Estados de preparación, lanzamiento y producción.
- Acciones de exportación, revisión y diagnóstico.

### Tono demasiado técnico

Se redujo la fricción editorial en paneles visibles. El cliente recibe mensajes de utilidad y el administrador mantiene contexto operativo sin mezclar idiomas.

### Inconsistencia de botones

Se reforzó el uso de acciones claras: abrir, ver, revisar, consultar, exportar, ejecutar y volver.

## Hallazgos no corregidos por alcance

- Estados técnicos contractuales como Sentinel, AutoPilot, Browser QA, Cron, Master Tick, Render, Stripe, Telegram y Codex se mantienen como nombres propios o contratos operativos.
- La salida de consola de Windows puede representar acentos como secuencias mojibake aunque el navegador no los muestre así. Browser QA marcó `mojibake_visible=false`.
- Checks antiguos V842/V849 contienen patrón vacío en su lista de detección y por eso pueden fallar aunque el producto esté limpio; se documentan como deuda del check, no como defecto visible.

## Riesgos restantes

- Algunas pantallas administrativas siguen usando nombres de sistemas porque forman parte del lenguaje operativo del producto.
- La certificación es local y debe revisarse visualmente antes de commit.
- Producción no queda certificada en este sprint.

## Decisión

La calidad lingüística visible queda en estado PASS LOCAL. No se detectan bloqueos editoriales para revisión humana.
