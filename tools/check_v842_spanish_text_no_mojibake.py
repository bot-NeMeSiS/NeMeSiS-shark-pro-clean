from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = [
    ROOT / "templates",
    ROOT / "static" / "app.css",
    ROOT / "app.py",
    ROOT / "engines",
]

FORBIDDEN = [
    "Ã",
    "Â",
    "",
    "Contrase?",
    "Configuraci?",
    "Pr?ximo",
    "Pr?ximos",
    "An?lisis",
    "revisi?",
    "conexi?",
    "p?blico",
    "env?o",
    "L?mite",
    "?ltim",
    "pa?s",
    "b?sico",
    "presi?",
    "estad?sticas",
    "Hist?rico",
    "HistÁrico",
    "dÁa",
    "dÁas",
    "membresÁa",
    "prÁximos",
    "bÁsicas",
    "bsqueda",
    "Evoluci?",
    "A?n",
    "{{ title or",
    "Lorem ipsum",
]

def iter_files():
    for item in SCAN_PATHS:
        if item.is_file():
            yield item
        elif item.is_dir():
            for path in item.rglob("*"):
                if path.suffix in {".html", ".py", ".css", ".js"}:
                    yield path

findings = []
for path in iter_files():
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for line_no, line in enumerate(text.splitlines(), 1):
        bad_tokens = [token for token in FORBIDDEN if token in line]
        if bad_tokens:
            # Some audit engines intentionally keep marker lists to detect mojibake.
            if "MOJIBAKE" in line or "mojibake" in line:
                continue
            findings.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "line": line_no,
                    "tokens": bad_tokens,
                    "text": line.strip()[:220],
                }
            )

payload = {"ok": not findings, "findings": findings[:100], "count": len(findings)}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
