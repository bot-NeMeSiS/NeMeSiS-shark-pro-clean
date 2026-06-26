from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    live = (ROOT / "templates" / "live.html").read_text(encoding="utf-8")
    for token in ["Sin directos reales ahora mismo", "Proveedor activo", "Guard anti-gasto activo", "v852_live_count"]:
        assert token in live, token
    print("V852 live API-Football real status OK")


if __name__ == "__main__":
    main()
