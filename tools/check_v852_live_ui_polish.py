from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    live = (ROOT / "templates" / "live.html").read_text(encoding="utf-8")
    assert "v852-live-empty-diagnostic" in live
    assert "v852-live-empty-diagnostic" in css
    assert "Sin directos reales" in live
    print("V852 live UI polish OK")


if __name__ == "__main__":
    main()
