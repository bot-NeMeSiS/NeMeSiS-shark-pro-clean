# V884 Sentinel And Visual Worker Functional QA

## Sentinel

Continuous Sentinel mantiene:

- no fake data;
- no deploy automatico;
- no llamadas externas pagadas;
- no writes peligrosos;
- proteccion admin/cron;
- reglas visuales previas.

## Nuevas reglas V884

- botones cliente con destino real;
- botones admin con destino operativo;
- href vacio/hash/javascript;
- cruces cliente/admin;
- picks con estado seguro;
- SHARK en modo seguro si OpenAI falta;
- pagos sin falso operativo;
- Telegram sin envios falsos.

## Visual Worker

El Visual Worker ahora produce:

- issues;
- grupos;
- tareas;
- prompts Codex;
- score;
- reglas funcionales;
- render awareness.

## Resultado esperado

V884 no reemplaza Sentinel: lo hace mas util para detectar problemas de flujo real.
