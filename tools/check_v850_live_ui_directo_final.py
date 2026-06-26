from pathlib import Path


def main():
    text = Path("templates/live.html").read_text(encoding="utf-8")
    required = ["data-v850-template=\"live\"", "v850-live-state", "v850-score-focus", "Minuto no disponible", "Sin directos reales", "Análisis SHARK"]
    for item in required:
        assert item in text, item
    assert "Baln" not in text and "Anlisis" not in text and "vaco" not in text
    print("check_v850_live_ui_directo_final OK")


if __name__ == "__main__":
    main()
