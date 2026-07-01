from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    home = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    assert "Hora España/Madrid" in home
    assert "lo primo" not in home
    assert "Result ados" not in home
    print("V852 home dashboard polish OK")


if __name__ == "__main__":
    main()
