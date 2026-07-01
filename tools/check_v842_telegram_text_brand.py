from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
files = [
    ROOT / "templates" / "telegram.html",
    ROOT / "templates" / "admin_telegram_command_center.html",
    ROOT / "app.py",
] + list((ROOT / "engines").glob("*telegram*.py"))

bad = ["Ã", "Â", "", "env?o", "conexi?", "autom?tico", "seg?n"]
findings = []
for path in files:
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for token in bad:
        if token in text:
            findings.append({"file": str(path.relative_to(ROOT)), "token": token})

payload = {
    "ok": not findings,
    "findings": findings,
    "telegram_templates_present": (ROOT / "templates" / "telegram.html").exists(),
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
