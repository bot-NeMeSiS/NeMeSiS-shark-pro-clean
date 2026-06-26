from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert (ROOT / "engines" / "crest_logo_experience_engine.py").exists()
    assert (ROOT / "templates" / "partials" / "team_identity.html").exists()
    for rel in ["templates/live.html", "templates/picks.html", "templates/match_detail.html"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "crest(" in text or "team_identity" in text, rel
    print("V852 crests/logos visual fallback OK")


if __name__ == "__main__":
    main()
