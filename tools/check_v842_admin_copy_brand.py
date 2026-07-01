from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
bad = ["Ã", "Â", "", "Configuraci?", "Pr?ximo", "L?mite", "?ltim", "membresÁa"]
findings = []
for path in (ROOT / "templates").glob("admin*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for token in bad:
        if token in text:
            findings.append({"file": str(path.relative_to(ROOT)), "token": token})

payload = {"ok": not findings, "findings": findings}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
