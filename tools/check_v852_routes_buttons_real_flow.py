from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    for href in ["/app", "/partidos", "/live", "/picks", "/shark", "/telegram", "/profile", "/support", "/logout"]:
        assert href in base or href in (ROOT / "templates" / "picks.html").read_text(encoding="utf-8"), href
    print("V852 routes/buttons real flow OK")


if __name__ == "__main__":
    main()
