"""Print a read-only media diagnostic for an explicit, existing SQLite path."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engines.highlight_read_model import read_highlights_readiness


def main():
    parser = argparse.ArgumentParser(description='Diagnóstico de metadatos, no certificación de publicación ni reproducción.')
    parser.add_argument('--db-path', required=True, help='Base SQLite existente; nunca se crea ni se migra.')
    args = parser.parse_args()
    result = read_highlights_readiness(args.db_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Success means the catalogue was readable, not that publication was certified.
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
