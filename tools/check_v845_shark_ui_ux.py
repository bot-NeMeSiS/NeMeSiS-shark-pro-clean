from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
shark = (ROOT / "templates" / "shark.html").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
required = [
    "data-v845-template=\"shark\"",
    "v845-shark-hero",
    "Preguntas rápidas",
    "Estado de datos",
    "Ver partidos",
    "Conectar Telegram",
    "V845 SHARK AI INTELLIGENCE PRODUCT ASSISTANT START",
]
missing = [item for item in required if item not in shark + css]
print({"ok": not missing, "missing": missing})
raise SystemExit(0 if not missing else 1)
