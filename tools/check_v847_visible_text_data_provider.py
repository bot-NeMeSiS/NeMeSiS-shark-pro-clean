from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
targets = [ROOT / "templates" / "admin_api_sports_audit.html", ROOT / "engines" / "api_sports_provider_engine.py"]
bad = ["Ã", "Â", "�", "undefined", "null"]
hits = []
for path in targets:
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in bad:
        if token in text:
            hits.append(f"{path.name}:{token}")
print({"bad_hits": hits})
raise SystemExit(1 if hits else 0)
