from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    assert "nemesis_brand('/app', 'sidebar')" in base
    assert "nemesis_brand('/admin/control-center', 'admin')" in base
    for token in ["ns-brand-sidebar", "ns-brand-admin", "v828-client-rail", "v808-admin-rail"]:
        assert token in css or token in base, token
    assert "object-fit: contain" in css
    print("V851 desktop logo/sidebar OK")


if __name__ == "__main__":
    main()
