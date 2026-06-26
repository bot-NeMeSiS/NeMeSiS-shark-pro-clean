from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    partial = (ROOT / "templates" / "partials" / "brand_logo.html").read_text(encoding="utf-8")
    assert "data-v852-shell" in base
    assert "nemesis_brand(_brand_href, 'topbar')" in base
    assert "nemesis_brand('/app', 'sidebar')" in base
    assert "nemesis_brand('/admin/control-center', 'admin')" in base
    assert "NeMeSiS" in partial and "SHARK PRO" in partial
    print("V852 logo brand regression OK")


if __name__ == "__main__":
    main()
