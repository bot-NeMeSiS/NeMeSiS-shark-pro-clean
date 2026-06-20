# V830 Mobile Screen By Screen QA

## Pantallas cliente revisadas

- `/`
- `/cliente-login`
- `/registro`
- `/app`
- `/partidos`
- `/calendar`
- `/live`
- `/directo`
- `/picks`
- `/shark`
- `/shark-core`
- `/profile`
- `/telegram`
- `/support`
- `/favorites`
- `/track-record`
- `/combis`
- `/mercados`
- `/highlights`
- `/match/<id>`

## Resultado

La corrección V830 es global al shell, por lo que todas las pantallas cliente heredan:

- bottom nav móvil centrada;
- 5 enlaces visibles;
- padding inferior para no tapar contenido;
- floating SHARK seguro;
- scroll-to-top oculto en móvil;
- protección de overflow horizontal;
- safe-area iOS en zona inferior;
- cards y contenedores con `max-width:100%`.

## Plantillas marcadas

Las plantillas reales ya cubiertas por V829 se marcaron también con `data-v830-template` y `v830-certified-screen` para trazabilidad de V830.

## Nota

No se inventaron datos deportivos ni se modificó lógica de partidos, picks, Telegram, SHARK o pagos.
