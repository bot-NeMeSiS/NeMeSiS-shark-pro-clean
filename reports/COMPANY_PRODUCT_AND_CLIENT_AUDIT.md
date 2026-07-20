# NeMeSiS SHARK PRO - Auditoría de producto y cliente

## Dictamen de experiencia

La experiencia V937 es visualmente sólida y deliberada. Las capturas revisadas muestran identidad consistente, jerarquía clara, estados vacíos honestos y separación real entre cliente y admin. La principal deuda de producto no es estética: es demostrar que los datos, membresías, pagos, Telegram y soporte que sostienen la promesa comercial funcionan de extremo a extremo en producción.

## Mapa de superficies

Leyenda de prueba: **D/M** = captura local desktop/móvil; **S** = smoke local; **P** = producción no certificada en esta auditoría.

| Superficie y rutas | Objetivo | Fuente/dependencias | Permiso | Estado/fallback | Prueba | Riesgo comercial |
|---|---|---|---|---|---|---|
| Home `/` | Explicar propuesta y actividad del día | DB/caché deportiva, catálogo | Público | Estado seguro si no hay agenda | D/M, S; P pendiente | Puede parecer inactiva si sync falla, pero no inventa datos |
| Registro `/registro` | Crear cuenta | SQLite, password hash, rate limit | Público | Error de formulario seguro | D/M, S | Privacidad/legal de alta pendiente de certificación |
| Login `/cliente-login`, `/login` | Autenticar cliente | Sesión, DB, rate limit | Público | Mensaje genérico | D/M, S | Cookie sin endurecimiento completo |
| Recuperación `/forgot-password`, `/reset-password/<token>` | Recuperar acceso | Token, identidad, canal de entrega | Público/token | Expiración/error seguro | Ruta presente; P no probado | Si no entrega token, usuario queda bloqueado |
| Dashboard `/app` | Centro diario y siguiente acción | Sesión, resumen deportivo, Telegram, plan | Cliente | Estado premium sin datos | D/M, S mock | Repite ceros si sync no existe; datos técnicos no visibles |
| Partidos `/calendar`, `/calendario`, `/partidos`, aliases | Agenda por fecha/competición | DB/caché, Madrid Time, logos | Público/cliente | Incompletos fuera de lista; mensaje seguro | D/M, S | Frescura real no certificada |
| Live `/live`, `/directo`, aliases | Partidos con evidencia real | DB/caché live, freshness gate | Público/cliente | Próximos/empty state | D/M, S y checks | Falso live sería daño reputacional alto |
| Resultados `/resultados`, `/track-record`, `/historico` aliases | Evidencia y aprendizaje | Picks liquidados/resultados evaluables | Público/cliente | Sin muestra evaluable | D/M, S | ROI no debe mostrarse con muestra insuficiente |
| Picks `/picks` | Selecciones publicables y explicación | Partido, mercado, selección, cuota, lifecycle | Público/cliente/plan | No publica incompletos | D/M, S y checks | Alta promesa comercial; exige source/freshness |
| Combis `/combis` | Combinaciones según plan | Picks completos y reglas | Cliente/plan | Sin combinación si faltan datos | Ruta presente; visual parcial | Riesgo de sobrepromesa y uso responsable |
| Detalle `/match/<id>`, `/partido/<id>` | Contexto de un encuentro | Partido, timeline, estadísticas, picks | Público/cliente | 404 contextual | Smokes dinámicos históricos | IDs/fuentes y freshness deben ser trazables |
| Favoritos `/favoritos`, `/favorites` | Guardar seguimiento | Sesión, SQLite | Cliente | Lista vacía | Ruta/smoke | Persistencia real no probada tras restart |
| SHARK `/shark`, `/shark-ai` | Director deportivo/contexto | DB, caché, OpenAI opcional | Cliente/plan | Modo seguro, recomienda esperar | D/M, benchmark local | No debe presentarse como predicción garantizada |
| Telegram `/telegram` | Extensión de alertas | Link code, bot, cola, dedupe | Cliente | Estado no conectado | D/M, S; envío real no | Afirmar conectado/envío sin evidencia |
| Perfil `/profile` | Cuenta, plan, preferencias | Sesión, DB, Stripe/Telegram | Cliente | Valores seguros | D/M, S mock | Derechos de privacidad no operables |
| Membresías `/memberships`, `/planes` | Comparar y convertir | Catálogo/env/Stripe | Público/cliente | CTA desactivado si no configurado | D/M, motor local | Precios divergentes y ELITE+ ambiguo |
| Soporte `/support` | Contacto y resolución | Formulario/DB o canal | Público/cliente | Mensaje de recepción | D/M, S | No hay SLA/ticketing real demostrado |
| Logout `/logout` | Cerrar sesión | Sesión | Cliente | Redirección | Checks V932 | Debe invalidar cookie y estado de cliente |
| Legales | Términos, privacidad, juego responsable | Contenido estático/config | Público | Navegación segura | Visual | Textos pendientes de revisión legal |
| PWA `/manifest.json`, `/service-worker.js` | Instalación/cache/offline seguro | Manifest, SW, assets | Público | Network-first para navegación | Local | Necesita certificación real de update/caché |
| 404/500 | Recuperación de errores | Error handlers, navegación | Público/API | HTML seguro/JSON | Smoke | No debe exponer traceback/internals |

## Permisos y membresías reales

| Tier | Implementación confirmada | Valor | Límite/riesgo |
|---|---|---|---|
| FREE | Tier de núcleo | Agenda, live cuando existe, contenido informativo, acceso limitado | Debe ser útil sin prometer picks diarios |
| PRO | Tier de núcleo | Más picks/recomendaciones, SHARK ampliado, Telegram premium, historial | Compra/renovación real no certificada |
| ELITE | Tier de núcleo | Límites altos, auto-picks/estadística avanzada/soporte | Claims y disponibilidad dependen de datos reales |
| ELITE+ | Etiqueta visual/legacy | No es entitlement independiente | Se normaliza a ELITE; no debe venderse como cuarto producto hasta implementarlo |
| ADMIN | Rol operativo | Acceso a command centers | Debe estar totalmente separado de cliente |

Las cifras de límites deben mantenerse en una fuente única. La auditoría encontró precios de estimación admin (19/49) distintos de los visibles por defecto (9.99/24.99).

## Revisión visual asistida

### Excelente

- Marca consistente, fondo oscuro propio y acentos cian/azul/dorado con significado.
- Navegación cliente/admin claramente separada.
- Home, calendario, picks, SHARK y membresías explican por qué hay o no contenido.
- Bottom nav móvil fija y específica.
- Copy responsable: calidad antes que cantidad, sin resultados garantizados.

### Muy bueno

- Cards, chips, CTA y estados seguros uniformes.
- Admin informa siguiente acción y bloqueo comercial.
- SHARK declara “modo seguro” y recomienda esperar cuando no hay evidencia.
- Login, perfiles y planes comparten sistema visual.

### Mejorable

- En móvil algunas barras de tabs/nav se cortan visualmente y dependen de scroll horizontal (por ejemplo, filtros Live y navegación admin).
- La ausencia de datos repite el mismo mensaje en banner, KPI, CTA y panel; puede sentirse redundante.
- Algunos hero/títulos consumen demasiado alto en desktop, desplazando valor útil.
- Botones móviles con copy largo envuelven a dos líneas.
- La experiencia admin móvil es funcional, pero densa y no prioriza solo las acciones de emergencia.

### Crítico para vender

- Datos deportivos reales/frescos no certificados en este corte.
- Pago, portal, webhook, cancelación y tier real no certificados.
- Legal y privacidad no cerrados.
- Soporte/SLA y recuperación de cuenta no probados end-to-end.

## Ciclo de vida deportivo esperado

```text
proveedor -> cache/DB -> validación de completitud -> Madrid Time
  -> próximo / live / finalizado / pendiente
  -> pick candidato -> completo/publicable/bloqueado
  -> cuota fresh/recorded/stale/invalid
  -> cierre -> grading -> track record evaluable
```

Reglas verificadas localmente:

- Live requiere evidencia y frescura.
- Stale e incompletos no cuentan en KPI ni arrays públicos.
- Pick necesita partido, mercado, selección y cuota válidos.
- Cuota 0 o expirada no debe publicarse.
- Sin muestra evaluable no debe presentarse ROI como rendimiento real.

## Recuperación desde la perspectiva del cliente

| Fallo | Qué debe ver | Acción recuperadora |
|---|---|---|
| Proveedor caído | Estado temporal, última sync pública sin detalle técnico | Reintento en background y acceso a histórico |
| Sin live | Próximos completos, no marcadores ficticios | Polling adaptativo |
| Sin picks | Regla de publicación y calendario | Nueva evaluación tras sync |
| SHARK no disponible | Modo seguro y navegación útil | No bloquear el resto de la app |
| Telegram caído | Estado no disponible, preferencias conservadas | Cola retenida/dry-run admin |
| Stripe caído | Plan actual conservado, no duplicar compra | Reconciliación webhook |
| Error interno | Error seguro con Inicio/Entrar/Soporte | Incident ID interno, no traceback |

## Conclusión

La experiencia está preparada para una beta privada visual y funcional. No debe abrirse una beta de pago hasta demostrar datos frescos, persistencia, Stripe, Telegram, privacidad/legal y recuperación.

