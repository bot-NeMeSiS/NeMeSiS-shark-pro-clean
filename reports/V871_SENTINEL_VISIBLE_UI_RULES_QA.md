# V871 Sentinel Visible UI Rules QA

## Nuevas reglas
Sentinel ahora detecta:
- texto repetido consecutivo en enlaces/botones;
- CTAs con palabras duplicadas;
- mantiene detección de mojibake, nav cliente en admin, floating duplicado, claims irresponsables y tokens técnicos visibles.

## Seguridad
Sentinel sigue siendo diagnóstico: no escribe código, no despliega, no toca secretos, no envía Telegram y no modifica pagos.

## Objetivo
Que una pantalla con `Panel Panel`, `SHARK SHARK` o botones similares no pueda pasar como “todo OK”.
