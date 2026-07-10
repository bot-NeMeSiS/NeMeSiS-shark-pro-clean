# V928 Render Real Client Desktop and Mobile QA

## Correcto en capturas reales

- Home, login, registro, calendario, live, picks, track record, SHARK y membresias renderizan el shell V928.
- Desktop y movil usan navegaciones distintas.
- Bottom navigation movil mantiene cinco accesos y safe-area; los controles siguen siendo desplazables y alcanzables.
- No se detecto overflow horizontal en capturas validas.
- No hay hero duplicado ni gran espacio superior vacio.
- Fallbacks de escudos se muestran sin inventar insignias.
- Calendario y live muestran datos de DB/cache; picks incompletos permanecen bloqueados.
- Detalle real devuelve 200 en los seis viewports.

## Regresiones demostradas y corregidas localmente

- El detalle volcaba listas/diccionarios completos en `Forma e historico`, produciendo una pagina extremadamente larga.
- Picks mostraba `Cuota media 0.71` pese a tener 0 picks completos.
- PRO/ELITE mostraban `/mes` dos veces.
- Home podia decir `Sin agenda real cargada` a la vez que mostraba 35 partidos hoy.
- Rutas deportivas podian sincronizar proveedores durante el render y bloquear Render.

## Autenticacion cliente

`/app`, `/profile` y `/telegram` redirigieron correctamente al login sin sesion. No se creo un usuario de produccion para la prueba, por lo que las vistas cliente autenticadas quedan pendientes.
