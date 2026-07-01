from pathlib import Path


def main():
    text = Path("templates/calendar.html").read_text(encoding="utf-8")
    for item in ["data-v850-template=\"calendar\"", "v850_live_card", "v850-live-pill", "España/Madrid", "Filtros rápidos", "País"]:
        assert item in text, item
    assert "EspaÁa" not in text and "Foco rpido" not in text
    print("check_v850_calendar_fixtures_crests OK")


if __name__ == "__main__":
    main()
