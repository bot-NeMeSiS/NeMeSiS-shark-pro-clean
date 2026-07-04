# V892/V894 User/Admin Journey QA

## Qué revisa

El worker revisa rutas publicas, cliente y admin con Flask test client:

- anonimo
- FREE
- PRO
- ELITE
- ADMIN

## Señales

- status HTTP
- 500/502
- 404 inesperado
- links falsos
- `None/null/undefined` visibles
- mojibake
- nav cliente en admin
- admin en cliente
- apuestas garantizadas

## Limitacion

No crea usuarios falsos en produccion y no declara navegador real si no se ejecutan capturas.
