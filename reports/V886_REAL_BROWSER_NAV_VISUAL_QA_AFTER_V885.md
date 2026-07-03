# V886 Real Browser Nav Visual QA After V885

## Objetivo

Validar si V885 corrigio de verdad el problema del menu lateral cliente y la navegacion duplicada.

## Disponibilidad de browser

Playwright no esta disponible de forma usable en este entorno local:

- El proyecto no tiene `playwright` instalado.
- El runtime de Codex expone un paquete `playwright`, pero falta `playwright-core`.

Por tanto, esta V886 no declara pixel-perfect ni capturas reales. La QA se hizo con Flask test client, HTML renderizado y contrato CSS responsive.

## Resultado

- Cliente desktop: sidebar V885 presente como `data-nav-zone="client-sidebar"`.
- Cliente movil: bottom nav preservada como `data-nav-zone="client-bottom"`.
- Admin: rail admin separado y sin sidebar cliente.
- No se detectan botones laterales duplicados en el contrato renderizado.
- No se detecta nav admin dentro de cliente.
- No se detecta nav cliente dentro de admin en rutas protegidas/sin sesion.

## Limitacion

No se midio `overflowX` real por navegador. Se valida por CSS/HTML y queda pendiente Browser QA real tras instalar Playwright o usar navegador disponible.
