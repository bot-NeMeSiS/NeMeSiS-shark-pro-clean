from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.blueprint_migration_engine import write_route_map, build_route_summary

if __name__ == "__main__":
    app_py = ROOT / "app.py"
    out = ROOT / "ROUTE_MAP_V606.md"
    write_route_map(out, app_py)
    summary = build_route_summary(app_py)
    print(f"OK - rutas detectadas: {summary['total_routes']}")
    print(f"Mapa generado: {out}")
