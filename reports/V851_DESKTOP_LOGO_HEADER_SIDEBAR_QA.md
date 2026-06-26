# V851 QA PC Logo/Header/Sidebar

## Revisado
- Topbar cliente.
- Rail cliente.
- Rail admin.
- Compatibilidad visual con V848/V849/V850.

## Cambios
- El rail cliente usa `nemesis_brand('/app', 'sidebar')`.
- El rail admin usa `nemesis_brand('/admin/control-center', 'admin')`.
- El icono mantiene `object-fit: contain` para no deformarse.
- Se conservan las clases históricas de rails para no romper estilos existentes.

## Resultado
La marca queda completa, alineada y consistente en PC, sin separar icono y texto por pantalla.
