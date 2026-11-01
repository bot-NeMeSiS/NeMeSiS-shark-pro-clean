# Cambios sin sorpresas

Estado: regla solicitada por el fundador el 29/10/2026; preparada para su
incorporación al repositorio. No concede autorización de producción.

## Antes de implementar

Dar un aviso breve en español: **qué cambia, dónde, por qué, qué se mantiene y
si afectará ahora a producción**. Explicar una retirada, cambio de fondo,
intensidad de marca, navegación, etiquetas, densidad o comportamiento, aunque
se considere una mejora. Si cambia el alcance, avisar de nuevo antes de editar.
No exigir confirmación para cada decisión delegada de bajo riesgo.

## Después de implementar

Entregar un recibo legible: cambio real frente al anterior, beneficio esperado
frente al medido, archivos/PR, pruebas con alcance, limitaciones, reversión y
estado exacto. Distinguir **propuesta / implementado en rama / CI / integrado /
desplegado y comprobado**. Nunca equiparar commit, CI verde o imagen aprobada
con aceptación visual final o funcionamiento certificado en producción.

En cambios visuales, enlazar `VISUAL_CHANGELOG.md` y una comparación antes/después
cuando sea posible. Indicar si las capturas son de la app real con sesiones
sintéticas, una composición estática o producción. Mantener idénticos datos y
viewport al comparar. Un test CSS no certifica legibilidad de todas las rutas.

## Límites que se conservan

No cambiar sin la autorización independiente correspondiente: merge/deploy,
planes/costes, secretos, cuotas, usuarios, pagos, DB_PATH, envíos externos o tareas
productivas. No añadir un modal cliente, consentimiento por cada ajuste ni
notificaciones públicas a todos los usuarios: este procedimiento informa al
fundador en el canal de trabajo y deja trazabilidad para Codex.

## Formato mínimo

**Aviso:** “Voy a cambiar X en Y para Z; se conserva W. Queda en borrador, no
cambia aún la web publicada.”

**Entrega:** “Se cambió X. Evidencia: … Limitaciones: … Estado: … Reversión: …”

Cuando no se puede ejecutar o comprobar algo, decirlo explícitamente en vez de
presentar una intención como un resultado.
