from pathlib import Path


def main():
    files = [Path("templates/live.html"), Path("templates/calendar.html"), Path("templates/match_detail.html"), Path("templates/admin_api_sports_audit.html"), Path("engines/live_match_experience_engine.py")]
    required = ["En directo", "Descanso", "Finalizado", "Próximo", "Resultado pendiente", "Minuto no disponible", "Esperando proveedor", "Sin directos reales", "Analizar con SHARK"]
    combined = "\n".join(p.read_text(encoding="utf-8") for p in files)
    for item in required:
        assert item in combined, item
    for bad in ["Ã", "Â", "", "Baln", "Anlisis"]:
        assert bad not in combined, bad
    print("check_v850_live_crests_text_state OK")


if __name__ == "__main__":
    main()
