from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
paths = list((ROOT / "templates").rglob("*.html")) + [ROOT / "static" / "app.css", ROOT / "app.py"]

forbidden = [
    "\ufffd",
    "Contrase?a",
    "contrase?a",
    "PA?S",
    "d?a",
    "d?as",
    "se?al",
    "se?ales",
    "Espa?a",
    "Andaluc?a",
    "{{ title or",
    "Lorem ipsum",
]

hits = []
for path in paths:
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in forbidden:
        if "?" in token and token[0].isalnum() and token[-1].isalnum():
            found = re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None
        else:
            found = token in text
        if found:
            hits.append({"file": str(path.relative_to(ROOT)), "token": token})

payload = {"ok": not hits, "hits": hits}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
