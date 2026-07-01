# V882 Core Product Gap Audit

| Área | Ruta | Estado real | Problema | Causa probable | Fix seguro | V882 |
|---|---|---|---|---|---|---|
| Partidos | `/partidos`, `/calendar` | Carga local OK con DB temporal | Si no hay datos, la pantalla podía parecer vacía o genérica | Cache/sync sin partidos o filtros activos | Estado “Sin partidos reales ahora mismo” con acción a semana/directo/admin | Sí |
| Live | `/live`, `/directo` | Carga local OK con DB temporal | Sin directos reales puede parecer poco vivo | Proveedor activo sin fixtures live o cache vacía | Mantener “Sin directos reales” y explicar guard/cache | Sí |
| Picks | `/picks` | Carga local OK con DB temporal, 0 picks | Sin picks puede parecer producto vacío | No hay picks publicados con cuota/selección válidas | Explicar cuota pendiente, selección pendiente y pick en revisión | Sí |
| Escudos | Cards partido/live/picks | Fallback disponible | Cache de logos puede estar en 0 | No sync de logos o proveedor sin datos | Fallback premium, sin imagen rota ni escudo inventado | Sí |
| Admin | Data Center/API panels | Protegido sin sesión | El dueño necesita causa, no solo paneles | Diagnósticos dispersos | Reportes V882 dejan trazabilidad y siguiente acción | Sí |
| Sentinel | Static QA | 10.0 previo | Score alto aunque el usuario vea vacío | Reglas demasiado genéricas | Regla V882 para rutas deportivas vacías sin explicación | Sí |

## Respuestas clave

1. `/partidos`: carga y ahora explica mejor si no hay partidos.
2. `/calendar`: carga y ahora explica mejor si no hay partidos.
3. `/live`: carga y mantiene estado seguro sin inventar directos.
4. `/directo`: alias funcional de directo.
5. `/picks`: carga y separa ausencia de picks como estado de revisión/cuotas/selección pendiente.
6. Relación partido → pick: se preserva cuando existe `pick_id`/`match_id`; no se inventa.
7. Cuotas reales: solo se muestran si existen; si no, “Cuota pendiente”.
8. Escudos: fallback premium preservado.
9. Cliente: ahora entiende mejor ausencia de datos.
10. Admin: queda documentada la necesidad de revisar sync/cache.
11. Sentinel: V882 añade regla específica.
12. Filtros: si ocultan todo, se sugiere limpiar/cambiar día/liga/semana.
13. Fecha Madrid: preservada.
14. API configurada sin sync: se documenta como causa probable.
15. Cache vacía: se documenta como causa probable.
