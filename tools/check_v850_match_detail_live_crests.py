from pathlib import Path


def main():
    text = Path("templates/match_detail.html").read_text(encoding="utf-8")
    for item in ["data-v850-template=\"match_detail\"", "v850-live-state", "Escudos", "Minuto no disponible", "Balón exacto no disponible", "Señal conectada"]:
        assert item in text, item
    assert "Baln" not in text and "Ubicacin" not in text and "Seal conectada" not in text
    print("check_v850_match_detail_live_crests OK")


if __name__ == "__main__":
    main()
