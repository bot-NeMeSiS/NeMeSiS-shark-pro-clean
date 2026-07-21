# V939 Pick Intelligence Pipeline QA

Pipeline validado en DB temporal aislada:

- 1 pick completo y con cuota de 5 minutos: `PREMIUM_READY`.
- 1 pick con cuota de 2 horas: `PROVIDER_STALE`.
- 1 pick sin mercado, seleccion ni cuota: `DATA_INCOMPLETE`.
- Publicacion automatica: no.
- Envio Telegram: no.
- Cambio de pesos: no.
- Escritura DB: 0.

El `quality_score` mide completitud del dato, no probabilidad de acierto. La DB local real no contiene candidatos suficientes para certificar valor deportivo real.

`PASS LOCAL`.
