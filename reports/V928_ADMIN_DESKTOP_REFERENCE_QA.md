# V928 Admin Desktop Reference QA

- Rutas reconstruidas: dashboard, Telegram Command Center, pagos, membresias, usuarios, picks, partidos, Data Center, Data Marketplace, automatizacion, certificacion y lanzamiento real.
- Rutas internas adaptadas: Workforce, Autonomous Company Sentinel, Issues, Outbox, Not Found y automatizacion diaria.
- Shell: sidebar fija, topbar, busqueda, identidad admin, estado operativo y navegacion exclusivamente admin.
- Contenido: KPIs reales, tablas compactas, acciones visibles, proveedor/estado y siguiente accion.
- Datos ausentes: se muestran como `Pendiente`, `Falta`, `Sin dato` o estado seguro; no como exito ficticio.
- Telegram: configuracion enmascarada y dry-run; no se envia desde la vista.
- Pagos: sin importes o usuarios de muestra; Stripe refleja configuracion real.
- Sentinel Issues: 679 registros historicos preservados; 40 visibles como maximo y 0 activos en el estado final probado.
- Browser QA admin: 13 rutas por 6 viewports, sin 500, 404 ni overflow.
- Separacion cliente/admin: confirmada.
