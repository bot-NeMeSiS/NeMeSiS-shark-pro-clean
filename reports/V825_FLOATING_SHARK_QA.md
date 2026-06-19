# V825 Floating Shark QA

## Objetivo

Reforzar un unico SHARK flotante premium sin duplicados.

## Resultado

- Cliente autenticado conserva un solo `shark-widget`.
- Publico no autenticado obtiene un enlace flotante ligero a `/shark`.
- `/shark` y `/shark-ai` ocultan el flotante.
- Admin no recibe floating shark cliente.
- Safe area aplicada para movil.
- `pointer-events` protegido para no bloquear contenido.

## Validacion

`tools/check_v825_floating_shark.py` paso correctamente.
