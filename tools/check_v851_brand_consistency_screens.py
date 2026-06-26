from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    partial = ROOT / "templates" / "partials" / "brand_logo.html"
    assert partial.exists()
    assert base.count("nemesis_brand(") >= 3
    assert "NeMeSiS" in partial.read_text(encoding="utf-8")
    assert "SHARK PRO" in partial.read_text(encoding="utf-8")
    for rel in [
        "templates/home.html",
        "templates/client_login.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/profile.html",
        "templates/telegram.html",
        "templates/support.html",
        "templates/admin_dashboard.html",
    ]:
        assert (ROOT / rel).exists(), rel
    print("V851 brand consistency screens OK")


if __name__ == "__main__":
    main()
