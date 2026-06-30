from pathlib import Path

FILES = [
    Path("templates/base.html"),
    Path("templates/client_app_center.html"),
    Path("templates/register.html"),
    Path("templates/profile.html"),
    Path("templates/admin_telegram_command_center.html"),
]

REPLACEMENTS = {
    "Automatización": "Automatización",
    "Membresías": "Membresías",
    "Navegación": "Navegación",
    "rápido": "rápido",
    "Histórico": "Histórico",
    "sesión": "sesión",
    "sesin": "sesión",
    "prximo": "próximo",
    "prxima": "próxima",
    "Operación": "Operación",
    "módulos": "módulos",
    "automatización": "automatización",
    "volvers": "volverás",
    "Lo prximo": "Lo próximo",
    "Sin foco prximo": "Sin foco próximo",
    "Vista previa del prximo mensaje": "Vista previa del próximo mensaje",
    "âŒ‚": "⌂",
    "â–¦": "▦",
    "â—": "●",
    "â—†": "◆",
    "â—¥": "SH",
    "â—Ž": "●",
    "â»": "⏻",
    "â†—": "↗",
    "âœˆ": "✈",
    "â˜°": "☰",
    "â™™": "♙",
    "âš½": "⚽",
    "â†»": "↻",
    "â˜€": "☀",
    "âš™": "⚙",
    "âœ“": "✓",
    "â–£": "▣",
    "â–¤": "▤",
    "â–§": "▧",
}


def main() -> None:
    changed = []
    for path in FILES:
        original = path.read_text(encoding="utf-8", errors="replace")
        text = original
        for bad, good in REPLACEMENTS.items():
            text = text.replace(bad, good)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(str(path))
    print({"changed": changed})


if __name__ == "__main__":
    main()
