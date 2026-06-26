from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    logo = ROOT / "static" / "img" / "shark-logo.svg"
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    assert logo.exists() and logo.stat().st_size > 100, "shark-logo.svg missing or empty"
    assert "rel=\"icon\"" in base and "img/shark-logo.svg" in base
    manifest = ROOT / "static" / "manifest.json"
    if manifest.exists():
        text = manifest.read_text(encoding="utf-8")
        assert "shark-logo.svg" in text or "icons" in text
    print("V851 logo assets/favicon/PWA OK")


if __name__ == "__main__":
    main()
