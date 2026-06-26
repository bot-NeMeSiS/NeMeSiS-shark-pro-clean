from pathlib import Path
import os, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir())/"nemesis_v849_compat.db"))
os.environ.setdefault("AUTOMATION_SECRET","codex-v849-secret")
import app as nemesis  # noqa
c=nemesis.app.test_client(); d=c.get("/api/runtime-version").get_json() or {}
checks={
 "v818":d.get("has_v818_automation") is True,
 "v844":d.get("has_v844_telegram_quality_filter") is True,
 "v845":d.get("has_v845_shark_ai_product_assistant") is True,
 "v847":d.get("has_v847_company_brain_api_sports_provider_qa") is True,
 "v848":d.get("has_v848_reference_shark_visual_pc_mobile") is True,
 "master_403":c.get("/api/automation/master-tick?dry_run=1").status_code==403,
 "master_200":c.get("/api/automation/master-tick?secret=codex-v849-secret&dry_run=1").status_code==200,
 "health_200":c.get("/api/automation/health-check?secret=codex-v849-secret").status_code==200,
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
