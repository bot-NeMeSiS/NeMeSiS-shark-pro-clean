from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    partial = (ROOT / "templates" / "partials" / "brand_logo.html").read_text(encoding="utf-8")
    assert "data-v851-shell" in base
    assert "nemesis_brand(_brand_href, 'topbar')" in base
    for token in ["ns-brand", "ns-brand-mark", "ns-brand-text", "ns-brand-name", "ns-brand-pro"]:
        assert token in partial, token
        assert token in css, token
    for token in ["max-width: min(58vw, 235px)", "@media (max-width: 390px)", "env(safe-area-inset-top)"]:
        assert token in css, token
    print("V851 mobile logo header OK")


if __name__ == "__main__":
    main()
