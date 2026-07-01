# V872 comparación contra referencia pantalla a pantalla

## Criterio

Sin captura nueva de navegador no se asigna pixel-perfect. Se comparan los puntos de V871 reportados y el runtime real de Render.

| Pantalla | Nivel actual estimado | Brecha principal | Corrección V872 |
| --- | ---: | --- | --- |
| `/app` PC | 8/10 | densidad y CTAs pueden depender de CSS aplicado en Render | CSS V872 protege acciones y ancho |
| `/picks` | 8/10 | evitar cards demasiado altas y texto largo | acciones compactas y estados con ancho limitado |
| `/live` | 8/10 | depende de datos reales y cache live | no se inventan directos; se mantiene fallback |
| `/partidos` | 8/10 | escudos reales dependen de cache 0 en Render | documentado fallback premium |
| `/shark` | 8/10 | OpenAI no configurado en Render | fallback seguro preservado |
| `/telegram` | 8/10 | depende de envíos reales no certificados | no filler/dedupe preservado |
| móvil | pendiente captura | no verificar sin navegador | overflow-x clip y flex-wrap |
| `/admin/dashboard` | 8/10 | evitar elementos cliente en admin | bloqueo CSS V872 para nav/widget cliente |
| `/admin/continuous-sentinel` | 8/10 | tablas/cards densas dependen de V871 | preservado |
| `/admin/sentinel-workflow` | 8/10 | acciones compactas | preservado + CSS V872 |

## Pendiente

Tras deploy V872, ejecutar captura real PC/móvil y vídeo de navegación para cerrar defectos visuales restantes.
