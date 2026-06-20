# V832 Full Ecosystem Links Buttons Audit

## Cliente

La navegación principal mantiene rutas reales: Entrar, Crear cuenta, Inicio, Partidos, Directo, Picks, SHARK, Perfil, Telegram, Soporte, Favoritos, Histórico, Combis, Mercados y Highlights.

La bottom nav cliente contiene cinco enlaces reales: `/app`, `/partidos`, `/live`, `/picks`, `/shark`.

## Admin

Las rutas admin principales se mantienen enlazadas desde el ecosistema existente: Dashboard, Mapa, Automatización, Telegram, Data Center, Usuarios, Membresías, Pagos, Certificación, Vista cliente y Health-check.

## Controles

Los checks V832 validan que la bottom nav exista una sola vez, que los enlaces principales estén presentes, que admin esté separado y que no haya variables Jinja literales tipo título roto.
