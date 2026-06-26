from pathlib import Path
import os
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v848_shark.db"))
import app as nemesis  # noqa: E402
engine = (ROOT / "engines" / "shark_ai_product_assistant_engine.py").read_text(encoding="utf-8", errors="replace")
client = nemesis.app.test_client()
checks = {
    "engine_exists": "answer_shark_question" in engine,
    "fallback": "build_fallback_answer" in engine,
    "no_hallucination": "Cuotas pendientes" in engine and "Resultado pendiente" in engine,
    "api_ask": client.get("/api/shark/ask?q=estado").status_code == 200,
    "admin_route": "/admin/shark-ai" in [str(r) for r in nemesis.app.url_map.iter_rules()],
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
