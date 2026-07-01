from pathlib import Path


def main():
    text = Path("templates/admin_api_sports_audit.html").read_text(encoding="utf-8")
    for item in ["data-v850-template=\"admin_api_sports_audit\"", "Live cacheado V850", "Escudos/logos", "Dry-run sin gastar crédito", "No se muestran secretos"]:
        assert item in text, item
    assert "API-SPORTS configurada" in text and "Sin llamadas por render" in text
    print("check_v850_admin_live_crests_provider OK")


if __name__ == "__main__":
    main()
