from pathlib import Path
import os, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir())/"nemesis_v849_shark.db"))
import app as nemesis  # noqa
css=(ROOT/"static/app.css").read_text(encoding="utf-8", errors="replace")
engine=(ROOT/"engines/shark_ai_product_assistant_engine.py").read_text(encoding="utf-8", errors="replace")
checks={
 "engine":"answer_shark_question" in engine and "build_fallback_answer" in engine,
 "api": nemesis.app.test_client().get("/api/shark/ask?q=estado").status_code==200,
 "visual_route": '[data-ns-route="/shark"]::after' in css,
 "no_floating_dup": '[data-ns-route="/shark"] .v825-public-floating-shark' in css,
 "admin": "/admin/shark-ai" in [str(r) for r in nemesis.app.url_map.iter_rules()],
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
