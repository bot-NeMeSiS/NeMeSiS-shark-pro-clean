from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    for rel in ["engines/api_sports_provider_engine.py", "engines/live_match_experience_engine.py", "engines/crest_logo_experience_engine.py"]:
        assert (ROOT / rel).exists(), rel
    app_py = (ROOT / "app.py").read_text(encoding="utf-8")
    for token in ["/admin/api-sports", "/api/admin/api-sports/status", "api_sports_configured"]:
        assert token in app_py, token
    print("V852 API-SPORTS live regression OK")


if __name__ == "__main__":
    main()
