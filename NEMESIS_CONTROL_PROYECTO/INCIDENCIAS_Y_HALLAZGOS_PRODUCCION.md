# Incidencias y Hallazgos de Produccion

## SPORTS-LIVE-STALE

- Evidencia: lecturas persistidas podian conservar LIVE despues de desaparecer
  de la respuesta del proveedor.
- Hotfix publicado: `fddbeea3` filtra snapshots obsoletos en la experiencia LIVE.
- Hallazgo local posterior: varios adaptadores aceptaban `updated_at` generico o
  write time como reloj de evidencia.
- Correccion candidata: `last_synced_at` viaja desde la observacion del proveedor
  hasta DB y superficies; Realtime, Directo, Calendario y dominio delegan en la
  verdad central.
- Estado: `FIXED_LOCAL_QA_PASS_PENDING_RELEASE_APPROVAL`.

## SPORTS-TERMINAL-LIVE-CONTRADICTION

- Riesgo: terminal, suspendido o resultado pendiente presentado como LIVE.
- Correccion candidata: FT/FINISHED/CANCELLED/POSTPONED/ABANDONED y SUSPENDED no
  pueden ser LIVE; un status ausente no se convierte en FT por horario.
- Evidencia: 27/27 tests focales y matriz 118/118.
- Estado: `FIXED_LOCAL_QA_PASS_PENDING_RELEASE_APPROVAL`.

## SPORTS-PARTIAL-SCORE

- Riesgo: convertir un solo gol conocido en `0-x` o `x-0` inventado.
- Correccion candidata: score visible solo con ambos lados; cero real se conserva.
- Estado: `FIXED_LOCAL_QA_PASS_PENDING_RELEASE_APPROVAL`.

## SPORTS-PROVIDER-DAILY-LIMIT

- Evidencia: pipeline productivo observado `PARTIAL`, autenticacion no confirmada,
  plan `INACCESSIBLE`, deep calls 0 y ultimo limite diario registrado.
- Comportamiento requerido: cache, estados honestos y nunca datos inventados.
- Estado: `EXTERNAL_LIMIT_OBSERVED`; no se genero trafico nuevo.

## API-LIVE-READ-MUTATION-DEBT

- Evidencia de codigo: `/api/live` puede activar sincronizacion de proveedor y
  escritura, aunque se consuma como lectura.
- Medida de esta fase: excluido de smoke y observacion repetitiva.
- Estado: `OPEN_SEPARATE_DESIGN_DEBT`; no invalida el candidato Sports Truth,
  pero requiere contrato explicito en un ciclo posterior.

## DIRECT-API-ADMIN-LINKS

- Evidencia: 21 enlaces de presentacion apuntan directamente a superficies
  API/admin.
- Clasificacion: deuda UX/presentacion; la autorizacion backend no se demostro rota.
- Estado: `OPEN_PRESENTATION_DEBT`.

## DOCUMENTATION-SPRAWL

- Evidencia: mas de dos mil entradas bajo `reports` y documentos historicos en raiz.
- Correccion: centro de control e indices por dominio; sin purga destructiva.
- Estado: `INDEXED_LOCAL`.

## V946-SPECIFICATION

- Busqueda: arbol, documentos y `git log --all -S V946` sin fuente original.
- Regla: no deducir alcance por numeracion ni por V944.
- Estado: `BLOCKED_ORIGINAL_SPEC_REQUIRED`.

## VISUAL-REFERENCE

- Evidencia historica: falsos PASS automaticos fueron rechazados por Founder.
- Estado: `NOT_REAUDITED`; no se modifico ni se declara PASS.

## SPORTS-CERTIFICATION

- La observacion real 3-7 dias no se reinicia.
- Esta ejecucion no inventa DAY, muestra LIVE Tier S/A ni cobertura no observada.
- Estado: `REAL_SPORTS_CERTIFICATION_IN_PROGRESS`.
