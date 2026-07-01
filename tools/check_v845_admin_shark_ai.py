from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8")
tpl = (ROOT / "templates" / "admin_shark_center.html").read_text(encoding="utf-8")
ok = all(s in app + tpl for s in ["/admin/shark-ai", "v845_shark_admin_summary", "OPENAI", "Telegram V844", "data-v845-template=\"admin_shark_center\""])
print({"ok": ok})
raise SystemExit(0 if ok else 1)
