from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "app.py").read_text(encoding="utf-8", errors="ignore")
ok = all(token in text for token in ("v844_quality", "blocked_preview", "last_no_filler", "top_football_only_no_filler"))
print({"ok": ok})
raise SystemExit(0 if ok else 1)
