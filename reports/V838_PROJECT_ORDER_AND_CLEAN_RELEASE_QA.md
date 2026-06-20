# V838 Project Order And Clean Release QA

## Orden de proyecto

No se borra a ciegas. Se preservan archivos activos y trazabilidad hist?rica. La limpieza se aplica en el ZIP final mediante exclusiones seguras.

## ZIP final

Debe excluir `.git`, `.venv`, cach?s, DB locales, WAL/SHM, logs, ZIPs internos, v?deos, capturas, backups y secretos.
