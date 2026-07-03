# Local Git Activity Audit

## Repo local

Carpeta:

```text
C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro
```

## Rama

`git branch --show-current`:

```text
main
```

Rama esperada: `main`.

Resultado: OK.

## Remoto

```text
origin  https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git (fetch)
origin  https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git (push)
```

Resultado: remoto local coincide con repo esperado.

## HEAD y tracking local

```text
HEAD:        a1be69cfe071435f34d0b3cc02a9a4bbdf4fdec2
origin/main: a1be69cfe071435f34d0b3cc02a9a4bbdf4fdec2
```

`git status --short --branch` antes de crear estos reportes:

```text
## main...origin/main
```

Lectura: local no mostraba cambios pendientes y el tracking local estaba alineado con `origin/main`. Esto depende de la ultima informacion local de Git; no sustituye un `fetch` real.

## Ultimos 20 commits locales

```text
a1be69c gfh
9d21208 uyikjy
02e826d gfh
54786f3 kj
233cb23 gf
a3157a8 gh
4d1e5a7 v
c30cd85 ´5
af7e6fc gj
40fa591 gg
a3fdfe3 hhg
0082979 mn
5384efa bnm
a68a9d7 f
597e07a nbm
4825403 lñk
7e47fbf gh
ab7402c bv
e14fcf2 jkl
c4d45b6 M,
```

## Archivos de raiz requeridos

```text
app.py             OK file
VERSION.txt        OK file
APP_VERSION        OK file
requirements.txt   OK file
templates          OK dir
static             OK dir
engines            OK dir
tools              OK dir
```

## Version local

```text
VERSION.txt: V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL
APP_VERSION: V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL
app.py APP_VERSION: V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL
```

## Runtime local

```json
{
  "app_version": "V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL",
  "version": "V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL",
  "version_txt": "V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL",
  "app_py_path": "C:\\Users\\aloha\\OneDrive\\Escritorio\\NeMeSiS shark pro\\app.py",
  "static_app_css_hash": "d9c4779f30c8b98e",
  "static_app_css_size": 911679,
  "has_v886_real_browser_nav_visual_qa": true,
  "has_v885_client_sidebar_restore": true
}
```

## Cambios sin subir

Antes de crear estos reportes de auditoria, `git status` estaba limpio respecto al tracking local. Despues de crear estos reportes, estos archivos quedan como cambios locales pendientes hasta que se haga commit/push.

## Veredicto

El proyecto local esta en V886, en rama `main`, con remoto configurado al repo esperado y raiz correcta. La rama local parece alineada con el tracking local `origin/main`, pero no se pudo hacer verificacion remota real por falta de acceso GitHub/HTTPS funcional.
