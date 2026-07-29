# Certificación de idioma español

Fecha Madrid: 2026-07-29
Estado: PASS LOCAL
Producción modificada: false
Commit: no realizado
Push: no realizado
Deploy: no realizado

## Alcance

Se revisó la copia visible de NeMeSiS SHARK PRO en cliente, administración y módulos deportivos principales:

- Landing, registro, login, perfil, configuración, membresías y estados vacíos.
- Home, dashboard, calendario, directo, picks, Telegram, SHARK y plataforma de acciones.
- Centro del partido, centro del equipo, centro de la competición y centro del jugador.
- Centro de operaciones, Developer Center, Company Board, Founder Mode, Sentinel, AutoPilot y paneles administrativos.
- Botones, menús, etiquetas, chips, tablas, mensajes, estados y CTAs visibles.

La revisión no cambia versión, arquitectura, Sports Core, SHARK, negocio, datos, producción ni integraciones externas.

## Resultado editorial

NeMeSiS queda con una línea de castellano más coherente, natural y comercial. Se corrigieron textos rotos por mojibake, acentos perdidos, mezclas innecesarias de inglés y español, terminología inconsistente y expresiones demasiado técnicas cuando eran visibles para usuario o administrador.

## Correcciones confirmadas

- Mojibake visible eliminado en textos de interfaz.
- Acentos restaurados en palabras frecuentes: contraseña, señal, próximo, configuración, sincronización, revisión, histórico, metodología, membresía, vinculación, diagnóstico, navegación y similares.
- Terminología deportiva unificada: partido, equipo, competición, jugador, fuente, evidencia, actualización, calidad y conocimiento.
- Terminología de producto unificada: panel, centro, plataforma, motor, pasarela, lanzamiento, preparación y salida a producción.
- Botones y acciones administrativas ajustadas a castellano claro.
- Tests actualizados para validar los nuevos textos oficiales cuando dependían de etiquetas visibles.
- Se conserva la separación entre texto comercial para cliente y texto operativo para administración.

## Terminología oficial aplicada

| Concepto previo | Forma visible oficial |
| --- | --- |
| Match | Partido |
| Team | Equipo |
| Competition | Competición |
| Player | Jugador |
| Match Center | Centro del partido |
| Team Center | Centro del equipo |
| Competition Center | Centro de la competición |
| Player Center | Centro del jugador |
| Sports Core | Modelo deportivo |
| Sports Knowledge | Conocimiento deportivo |
| Sports Graph | Grafo deportivo |
| Match Intelligence | Inteligencia del partido |
| SHARK Intelligence | Inteligencia SHARK |
| User Intelligence | Inteligencia de usuario |
| Decision Engine | Motor de decisiones |
| Gateway | Pasarela |
| Evidence | Evidencia |
| Freshness | Actualización |
| Quality | Calidad |
| Source | Fuente |
| Dashboard | Panel |
| Operations Center | Centro de operaciones |
| Developer Center | Centro de desarrollo |
| Founder Dashboard | Panel fundador |
| Company Command Center | Centro de mando de empresa |

## QA ejecutada

| Validación | Resultado | Evidencia |
| --- | --- | --- |
| py_compile app.py | PASS | app.py compila correctamente |
| compileall app.py engines tools | PASS | Sin errores de compilación |
| Jinja | PASS | 194 templates parseados sin errores |
| pytest completo | PASS | Suite completa en entorno local con DB temporal |
| Smoke Flask rutas reales | PASS | 29 rutas probadas, 0 fallos |
| Imports/rutas | PASS | 695 rutas registradas, plantillas y estáticos requeridos presentes |
| Route/link audit | PASS | 747 rutas, 1003 enlaces auditados, 0 enlaces rotos |
| Sentinel estático | PASS | score 10.0, 0 incidencias abiertas |
| Privacy/Secret Guard | PASS | 1052 archivos escaneados, 0 secretos confirmados |
| Browser QA | PASS | 72 checks, 24 escenarios, desktop/tablet/móvil, 0 fallos |

## Limitaciones

- La certificación es local. No declara Render ni producción certificados.
- Algunos checks históricos de texto V842/V849 tienen falsos positivos por incluir una cadena vacía como patrón; no se modificaron por estar fuera del alcance funcional.
- El Browser QA muestra muestras de texto en consola con codificación del terminal de Windows, pero el inspector marcó `mojibake_visible=false` en todos los escenarios.

## Decisión

PASS LOCAL.

NeMeSiS queda editorialmente preparado a nivel local para revisión humana de producto. La siguiente acción debe ser revisar visualmente las capturas finales y autorizar, si procede, un commit separado de certificación lingüística.
