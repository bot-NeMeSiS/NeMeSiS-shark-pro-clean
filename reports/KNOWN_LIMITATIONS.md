# KNOWN LIMITATIONS

Fecha Madrid: 2026-07-29

Alcance: limitaciones conocidas para beta cerrada.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

NeMeSiS esta preparado localmente como producto amplio, pero la beta debe ser honesta. Algunas areas estan listas para que usuarios prueben valor; otras necesitan certificacion antes de abrirse como promesa comercial.

## Limitaciones Operativas

| Area | Limitacion | Impacto | Mensaje beta |
| --- | --- | --- | --- |
| Produccion | Debe recertificarse antes de invitar usuarios | No asumir estado actual | "La beta se abre solo tras health y runtime certificados." |
| Render | Configuracion declarada single-instance | No probar escala masiva | "Beta cerrada con usuarios limitados." |
| Cron | Historico reciente marco `PARTIAL`/master tick pendiente en informes | Datos o ticks pueden requerir revision | "La frescura se verificara antes de pruebas sensibles." |
| Backup/restore | Restore aislado pendiente para beta ampliada | Riesgo continuidad | "No ampliar beta sin restore probado." |
| Alertas | Observabilidad externa no cerrada | Fallos pueden depender de revision humana | "Monitorizacion reforzada durante beta." |

## Limitaciones De Datos Deportivos

- Algunos datos pueden aparecer como "No disponible".
- Los datos stale deben mostrarse como antiguos, no como actuales.
- No todos los partidos tendran escudos, eventos, estadisticas, arbitro o estadio.
- No debe mostrarse live si no hay evidencia real.
- No se deben crear picks con datos incompletos o contradictorios.
- Fuentes nuevas no se conectan sin registro y aprobacion legal en Gateway.

## Limitaciones De SHARK

- SHARK no es IA generativa en esta fase.
- SHARK no garantiza resultados.
- SHARK no debe presentar hipotesis como hechos.
- SHARK depende de evidencia, frescura y calidad de datos.
- Si falta evidencia, debe decirlo o permanecer en silencio.

## Limitaciones De Telegram

- Telegram real puede estar desactivado o limitado.
- No se debe enviar contenido para rellenar.
- No debe haber envios masivos durante primera beta.
- Dedupe, limites y destino deben certificarse antes de uso real.
- El usuario debe saber que Telegram beta puede no estar activo.

## Limitaciones De Stripe Y Membresias

- Stripe debe permanecer en modo test hasta certificacion completa.
- No debe cobrarse a usuarios reales sin checkout, webhook, activacion y cancelacion certificados.
- FREE/PRO/ELITE deben explicarse sin promesas de beneficio.
- Si hay acceso beta manual, debe etiquetarse como beta/manual.

## Limitaciones De Soporte

- El soporte inicial es manual.
- No hay SLA publico.
- La respuesta beta debe tener objetivo interno, no promesa contractual.
- Cancelaciones, privacidad y pagos deben escalarse a Owner si hay duda.

## Limitaciones De Privacidad Y Metricas

- User Intelligence esta preparada, pero las metricas reales de beta deben minimizar datos.
- No se deben recoger datos innecesarios.
- No se debe vender informacion.
- No se debe enviar perfil de usuario a terceros.
- El usuario debe poder desactivar, exportar o borrar preferencias cuando el flujo este activo.

## Limitaciones Comerciales

- No hay conversion real medida.
- No hay cohortes de retencion.
- No hay evidencia de MRR, ARPU, churn o LTV real.
- Los objetivos de beta son hipotesis, no datos.
- No debe declararse Release 1.0 publica solo por pasar QA local.

## Limitaciones De Escala

- Decenas de miles de usuarios requieren pruebas de carga.
- SQLite puede ser cuello de botella bajo escritura concurrente.
- Render single-instance no es garantia de alta disponibilidad.
- Jobs y cron deben separarse/medirse antes de escala.

## Como Comunicar Estas Limitaciones

Correcto:

- "Esta informacion no esta disponible."
- "Este dato requiere verificacion."
- "La beta esta limitada para aprender con seguridad."
- "SHARK trabaja con evidencia, no con promesas."

Incorrecto:

- "Seguro que va a ganar."
- "Datos en tiempo real garantizados."
- "Telegram siempre enviara."
- "Pago activado automaticamente" si no esta certificado.
- "Release comercial lista" sin gates cerrados.

## Criterio Para Retirar Una Limitacion

Una limitacion se retira solo si:

- existe evidencia;
- se ejecuto QA;
- hay responsable;
- se actualizo documentacion;
- no introduce riesgo P1/P0;
- produccion se certifico si aplica.

## Siguiente Unica Accion

Antes de invitar usuarios, convertir estas limitaciones en un mensaje breve de beta para que nadie confunda producto en pruebas con lanzamiento publico completo.
