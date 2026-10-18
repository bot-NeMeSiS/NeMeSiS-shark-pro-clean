# Acceso a NeMeSiS desde el PC

El acceso **NeMeSiS Centro de Mando** del Escritorio abre una página local con el logo oficial y enlaces a Founder OS, administración, la app, resúmenes para clientes, control administrativo de resúmenes, Render y esta carpeta. El acceso de administración lleva al panel si ya tienes sesión o a la pantalla de inicio de sesión si hace falta autenticarte; el centro no guarda contraseñas.

Desde el Centro de mando, **Archivos del proyecto** abre los archivos locales dentro del navegador. Para abrir la carpeta en el Explorador de Windows, usa el acceso directo independiente **NeMeSiS Proyecto** del Escritorio. **Resúmenes para clientes** muestra solo vídeos cuyo uso está autorizado; **Control de resúmenes** abre el panel protegido para revisar el catálogo y los derechos. El panel **Centro de control** abre Founder OS en la plataforma publicada; sus acciones siguen protegidas por el inicio de sesión y permisos de administración. La consola de Render requiere una sesión propia de Render.

Para volver a crear los accesos directos, abre PowerShell en esta carpeta y ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\local_desktop\install_pc_access_shortcuts.ps1
```

## App local de pruebas

`tools\local_desktop\start_nemesis_local.cmd` inicia una copia local segura de pruebas. Esa copia no es la producción, usa datos locales separados y bloquea integraciones reales. Este PC no tiene creado el entorno `.venv` que necesita el lanzador y el repositorio fija Python 3.11.9; por eso ese acceso local no está listo todavía. Usa **NeMeSiS Administracion** para gestionar la plataforma real.
