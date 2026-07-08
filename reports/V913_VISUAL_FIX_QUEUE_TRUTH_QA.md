# V913 Visual Fix Queue Truth QA

## Estado de cola

- Total: `18`.
- Bloqueados por falta de screenshot: `18`.
- Listos para Codex con screenshot: `0`.
- Fixed by V913: `0`.
- Pixel-perfect permitido: `false`.

## Politica

Sin capturas reales no se desbloquea ningun item ni se marca como resuelto visualmente.

Estados validos V913:

- `BLOCKED_NO_SCREENSHOT`
- `READY_FOR_CODEX`
- `FIXABLE_SAFE`
- `FIXED_BY_V913`
- `NEEDS_HUMAN_VISUAL_REVIEW`
- `DANGEROUS_REQUIRES_APPROVAL`

Todos los items actuales quedan bloqueados hasta Browser QA real o importacion de resultados.
