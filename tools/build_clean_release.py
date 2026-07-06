#!/usr/bin/env python3
"""Build a clean Render-ready release ZIP for NeMeSiS SHARK PRO."""
from __future__ import annotations

import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION.txt"
VERSION = VERSION_FILE.read_text(encoding="utf-8-sig").strip() if VERSION_FILE.exists() else "DEV"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
VERSION_PREFIX = VERSION.split("_", 1)[0] if VERSION else "DEV"
MANIFEST_NAME = f"RELEASE_MANIFEST_{VERSION_PREFIX}.json"
MANIFEST_PATH = ROOT / MANIFEST_NAME


def release_output_dir() -> Path:
    preferred = ROOT.parent / "releases"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".codex_release_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback = ROOT / "release_output"
        fallback.mkdir(exist_ok=True)
        return fallback


OUT_DIR = release_output_dir()
OUT = OUT_DIR / ZIP_NAME

INCLUDE_TOP_LEVEL_DIRS = {
    "blueprints",
    "docs",
    "engines",
    "services",
    "static",
    "templates",
    "tests",
    "tools",
    "reports",
    "reference_images",
}
INCLUDE_TOP_LEVEL_FILES = {
    ".env.example",
    ".env.render.clean",
    ".gitignore",
    "APP_VERSION",
    "app.py",
    "database_manager.py",
    "Procfile",
    "pytest.ini",
    "README_MASTER.md",
    "render.yaml",
    "requirements-dev.txt",
    "requirements.txt",
    "runtime.txt",
    "VERSION.txt",
    "CODEX_DAILY_AUTOMATION_GUIDE.md",
    "CHATGPT_CONTINUATION_REPORT.md",
    "V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM_REPORT.md",
    "V723_TOTAL_PURGE_AUDIT_REPORT.md",
    "V724_SUPREME_CLIENT_VISUAL_EXPERIENCE_PRO_REPORT.md",
    "CLIENT_VISUAL_SYSTEM_V724.md",
    "V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX_REPORT.md",
    "MADRID_TIME_AUDIT_V725.md",
    "V726_TOTAL_PROJECT_CLEANUP_LIVE_EXPERIENCE_ORGANIZATION_REPORT.md",
    "V726_PROJECT_TREE_AUDIT.md",
    "V726_PURGE_REPORT.md",
    "V726_LIVE_EXPERIENCE_QA_REPORT.md",
    "V727_TELEGRAM_RELIABILITY_COMMAND_CENTER_REPORT.md",
    "TELEGRAM_RELIABILITY_AUDIT_V727.md",
    "TELEGRAM_RUNBOOK_V727.md",
    "V728_FINAL_CLIENT_EXPERIENCE_MADRID_TIME_LIVE_POLISH_REPORT.md",
    "V728_VISUAL_TIME_QA_REPORT.md",
    "RELEASE_MANIFEST_V723.json",
    "RELEASE_MANIFEST_V724.json",
    "RELEASE_MANIFEST_V725.json",
    "RELEASE_MANIFEST_V726.json",
    "RELEASE_MANIFEST_V727.json",
    "RELEASE_MANIFEST_V728.json",
    "V729_SECURITY_STABILITY_VISUAL_QA_FOUNDATION_REPORT.md",
    "V729_SECURITY_AUDIT.md",
    "V729_ROOT_HTML_DUPLICATES_AUDIT.md",
    "RELEASE_MANIFEST_V729.json",
    "V730_ARCHITECTURE_ROUTE_HEALTH_VISUAL_QA_FOUNDATION_REPORT.md",
    "V730_ARCHITECTURE_ROADMAP.md",
    "ROUTE_HEALTH_AUDIT_V730.md",
    "RELEASE_MANIFEST_V730.json",
    "V731_CLIENT_EXPERIENCE_QA_POLISH_FOUNDATION_REPORT.md",
    "V731_CLIENT_EXPERIENCE_QA_REPORT.md",
    "RELEASE_MANIFEST_V731.json",
    "V732_PRODUCTION_READINESS_CONTROL_CENTER_REPORT.md",
    "RELEASE_MANIFEST_V732.json",
    "V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH_REPORT.md",
    "RELEASE_MANIFEST_V733.json",
    "V734_PUBLIC_LAUNCH_TRACK_RECORD_PAYMENTS_FOUNDATION_REPORT.md",
    "V734_PUBLIC_LAUNCH_ROADMAP.md",
    "RELEASE_MANIFEST_V734.json",
    "V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION_REPORT.md",
    "V735_GO_LIVE_CHECKLIST.md",
    "RELEASE_MANIFEST_V735.json",
    "V736_GLOBAL_CLIENT_VISUAL_MEMBERSHIP_EXPERIENCE_REPORT.md",
    "V736_VISUAL_SYSTEM_QA_REPORT.md",
    "V737_NATIVE_APP_FEEL_MICROINTERACTIONS_NAVIGATION_POLISH_REPORT.md",
    "V737_APP_FEEL_QA_REPORT.md",
    "V738_FINAL_COMMERCIAL_RELEASE_CANDIDATE_POLISH_REPORT.md",
    "V738_FINAL_RELEASE_QA_REPORT.md",
    "V738_FINAL_RELEASE_CHECKLIST.md",
    "V739_SALE_READY_HOME_DATA_PRODUCTION_FIX_REPORT.md",
    "V739_SELL_READY_VALIDATION_CHECKLIST.md",
    "RELEASE_MANIFEST_V739.json",
    "V740_CLIENT_VISUAL_PICK_ANALYSIS_PERFECTION_REPORT.md",
    "V740_VISUAL_PERFECTION_QA_REPORT.md",
    "V740_VISUAL_CLIENT_SELL_READY_CHECKLIST.md",
    "RELEASE_MANIFEST_V740.json",
    "V741_CALENDAR_SEARCH_EXPERIENCE_PERFECTION_REPORT.md",
    "V741_CALENDAR_EXPERIENCE_QA_REPORT.md",
    "V741_CALENDAR_SELL_READY_CHECKLIST.md",
    "RELEASE_MANIFEST_V741.json",
    "V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH_REPORT.md",
    "V742_LIVE_EXPERIENCE_QA_REPORT.md",
    "V742_MATCH_DETAIL_QA_REPORT.md",
    "V742_TRACK_RECORD_ROI_QA_REPORT.md",
    "V742_TELEGRAM_PRODUCTION_QA_REPORT.md",
    "V742_SELL_READY_FINAL_CHECKLIST.md",
    "V742_ULTIMATE_PRODUCT_PERFECTION_DIFF.patch",
    "V742_PROJECT_CLEANUP_AUDIT.md",
    "V742_DUPLICATES_AND_LEGACY_AUDIT.md",
    "V742_FINAL_TREE_AUDIT.md",
    "CONTENT_RIGHTS_POLICY_V742.md",
    "V742_CONTENT_RIGHTS_QA_REPORT.md",
    "TELEGRAM_AUTOMATION_RENDER_SETUP_V742.md",
    "V742_TELEGRAM_AUTOMATION_FIX_REPORT.md",
    "V742_TELEGRAM_DESTINATION_QA_REPORT.md",
    "V742_TELEGRAM_PRODUCTION_RUNBOOK.md",
    "RELEASE_ZIP_AUDIT_V742.md",
    "RELEASE_MANIFEST_V742.json",
    "V743_DATA_VAULT_BACKUP_BUSINESS_INTELLIGENCE_PROTECTION_REPORT.md",
    "DATA_BACKUP_RUNBOOK_V743.md",
    "DATA_OWNERSHIP_AND_BUSINESS_VALUE_V743.md",
    "RELEASE_ZIP_AUDIT_V743.md",
    "RELEASE_MANIFEST_V743.json",
    "V744_PRODUCTION_RENDER_TELEGRAM_CERTIFICATION_AND_REAL_QA_REPORT.md",
    "V744_TELEGRAM_CERTIFICATION_QA_REPORT.md",
    "V744_RENDER_RUNTIME_QA_REPORT.md",
    "V744_PRODUCTION_ROUTES_QA_REPORT.md",
    "RENDER_PRODUCTION_VALIDATION_RUNBOOK_V744.md",
    "RELEASE_ZIP_AUDIT_V744.md",
    "RELEASE_MANIFEST_V744.json",
    "V745_TOP_APP_INTELLIGENCE_ALERTS_DEEP_DATA_COMMERCIAL_POLISH_REPORT.md",
    "V745_MATCH_INTELLIGENCE_QA_REPORT.md",
    "V745_VIDEO_HIGHLIGHTS_QA_REPORT.md",
    "V745_DEEP_DATA_FOUNDATION_REPORT.md",
    "V745_ALERTS_FOUNDATION_REPORT.md",
    "PAYMENTS_REAL_LAUNCH_ROADMAP_V745.md",
    "RELEASE_ZIP_AUDIT_V745.md",
    "RELEASE_ZIP_AUDIT_V748.md",
    "RELEASE_ZIP_AUDIT_V749.md",
    "RELEASE_ZIP_AUDIT_V749B.md",
    "RELEASE_ZIP_AUDIT_V750.md",
    "RELEASE_ZIP_AUDIT_V751.md",
    "RELEASE_ZIP_AUDIT_V752.md",
    "RELEASE_ZIP_AUDIT_V753.md",
    "RELEASE_ZIP_AUDIT_V754.md",
    "RELEASE_ZIP_AUDIT_V755.md",
    "RELEASE_ZIP_AUDIT_V756.md",
    "RELEASE_ZIP_AUDIT_V757.md",
    "RELEASE_ZIP_AUDIT_V758.md",
    "RELEASE_MANIFEST_V757.json",
    "RELEASE_MANIFEST_V758.json",
    "RELEASE_MANIFEST_V760.json",
    "RELEASE_MANIFEST_V761.json",
    "RELEASE_MANIFEST_V762.json",
    "RELEASE_MANIFEST_V745.json",
    "V747_ADMIN_TELEGRAM_MEMBERSHIP_DAYS_TIME_ORDER_REPORT.md",
    "RELEASE_MANIFEST_V747.json",
}
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "release",
    "release_output",
    "releases",
    "tmp",
    "temp",
    "backups",
    "logs",
    "v636work",
    "archive_legacy",
    "reports/archive",
    ".codex",
    ".agents",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-wal",
    ".db-shm",
    ".sqlite-wal",
    ".sqlite-shm",
    ".db-journal",
    ".sqlite-journal",
    ".log",
    ".zip",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".orig",
    ".bak",
    ".backup",
    ".old",
    ".tmp",
}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
SECRET_NAME_MARKERS = ("secret", "token", "private_key", "id_rsa")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unavailable"


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if not parts:
        return False
    rel_posix = rel.as_posix()
    if parts[0] == "reports":
        return (
            rel_posix == "reports/CODEX_DAILY_PROMPT_CURRENT.txt"
            or rel_posix.startswith("reports/v810_telegram_previews/")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V759")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V760")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V761")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V762")
            or rel_posix.startswith("reports/V748_")
            or rel_posix.startswith("reports/V749_")
            or rel_posix.startswith("reports/V749B_")
            or rel_posix.startswith("reports/V750_")
            or rel_posix.startswith("reports/V751_")
            or rel_posix.startswith("reports/V752_")
            or rel_posix.startswith("reports/V753_")
            or rel_posix.startswith("reports/V754_")
            or rel_posix.startswith("reports/V755_")
            or rel_posix.startswith("reports/V756_")
            or rel_posix.startswith("reports/V757_")
            or rel_posix.startswith("reports/V758_")
            or rel_posix.startswith("reports/V759_")
            or rel_posix.startswith("reports/V760_")
            or rel_posix.startswith("reports/V761_")
            or rel_posix.startswith("reports/V762_")
            or rel_posix.startswith("reports/V763_")
            or rel_posix.startswith("reports/V764_")
            or rel_posix.startswith("reports/V765_")
            or rel_posix.startswith("reports/V766_")
            or rel_posix.startswith("reports/V767_")
            or rel_posix.startswith("reports/V768_")
            or rel_posix.startswith("reports/V769_")
            or rel_posix.startswith("reports/V771_")
            or rel_posix.startswith("reports/V772_")
            or rel_posix.startswith("reports/V773_")
            or rel_posix.startswith("reports/V774_")
            or rel_posix.startswith("reports/V775_")
            or rel_posix.startswith("reports/V776_")
            or rel_posix.startswith("reports/V777_")
            or rel_posix.startswith("reports/V778_")
            or rel_posix.startswith("reports/V779_")
            or rel_posix.startswith("reports/V780_")
            or rel_posix.startswith("reports/V781_")
            or rel_posix.startswith("reports/V782_")
            or rel_posix.startswith("reports/V783_")
            or rel_posix.startswith("reports/V784_")
            or rel_posix.startswith("reports/V785_")
            or rel_posix.startswith("reports/V786_")
            or rel_posix.startswith("reports/V787_")
            or rel_posix.startswith("reports/V788_")
            or rel_posix.startswith("reports/V789_")
            or rel_posix.startswith("reports/V790_")
            or rel_posix.startswith("reports/V791_")
            or rel_posix.startswith("reports/V792_")
            or rel_posix.startswith("reports/V793_")
            or rel_posix.startswith("reports/V794_")
            or rel_posix.startswith("reports/V795_")
            or rel_posix.startswith("reports/V796_")
            or rel_posix.startswith("reports/V797_")
            or rel_posix.startswith("reports/V798_")
            or rel_posix.startswith("reports/V799_")
            or rel_posix.startswith("reports/V800_")
            or rel_posix.startswith("reports/V801_")
            or rel_posix.startswith("reports/V802_")
            or rel_posix.startswith("reports/V803_")
            or rel_posix.startswith("reports/V804_")
            or rel_posix.startswith("reports/V805_")
            or rel_posix.startswith("reports/V806_")
            or rel_posix.startswith("reports/V812_")
            or rel_posix.startswith("reports/V813_")
            or rel_posix.startswith("reports/V814_")
            or rel_posix.startswith("reports/V815_")
            or rel_posix.startswith("reports/V816_")
            or rel_posix.startswith("reports/V817_")
            or rel_posix.startswith("reports/V818_")
            or rel_posix.startswith("reports/V819_")
            or rel_posix.startswith("reports/V820_")
            or rel_posix.startswith("reports/V821_")
            or rel_posix.startswith("reports/V822_")
            or rel_posix.startswith("reports/V823_")
            or rel_posix.startswith("reports/V824_")
            or rel_posix.startswith("reports/V825_")
            or rel_posix.startswith("reports/V826_")
            or rel_posix.startswith("reports/V827_")
            or rel_posix.startswith("reports/V828_")
            or rel_posix.startswith("reports/V829_")
            or rel_posix.startswith("reports/V830_")
            or rel_posix.startswith("reports/V832_")
            or rel_posix.startswith("reports/V833_")
            or rel_posix.startswith("reports/V836_")
            or rel_posix.startswith("reports/V837_")
            or rel_posix.startswith("reports/V838_")
            or rel_posix.startswith("reports/V840_")
            or rel_posix.startswith("reports/V841_")
            or rel_posix.startswith("reports/V842_")
            or rel_posix.startswith("reports/V843_")
            or rel_posix.startswith("reports/V844_")
            or rel_posix.startswith("reports/V845_")
            or rel_posix.startswith("reports/V847_")
            or rel_posix.startswith("reports/V848_")
            or rel_posix.startswith("reports/V849_")
            or rel_posix.startswith("reports/V850_")
            or rel_posix.startswith("reports/V851_")
            or rel_posix.startswith("reports/V852_")
            or rel_posix.startswith("reports/V853_")
            or rel_posix.startswith("reports/V854_")
            or rel_posix.startswith("reports/V855_")
            or rel_posix.startswith("reports/V856_")
            or rel_posix.startswith("reports/V857_")
            or rel_posix.startswith("reports/V858_")
            or rel_posix.startswith("reports/V859_")
            or rel_posix.startswith("reports/V860_")
            or rel_posix.startswith("reports/V861_")
            or rel_posix.startswith("reports/V862_")
            or rel_posix.startswith("reports/V863_")
            or rel_posix.startswith("reports/V864_")
            or rel_posix.startswith("reports/V865_")
            or rel_posix.startswith("reports/V866_")
            or rel_posix.startswith("reports/V867_")
            or rel_posix.startswith("reports/V868_")
            or rel_posix.startswith("reports/DAILY_")
            or rel_posix.startswith("reports/V811_")
            or rel_posix.startswith("reports/V810_")
            or rel_posix.startswith("reports/V809_")
            or rel_posix.startswith("reports/V808_")
            or rel_posix.startswith("reports/V807_")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V806")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V811")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V810")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V809")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V808")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V807")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V765")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V766")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V767")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V768")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V769")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V771")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V772")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V773")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V774")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V775")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V776")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V777")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V778")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V779")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V780")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V781")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V782")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V783")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V784")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V785")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V786")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V787")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V788")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V789")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V790")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V791")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V792")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V793")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V794")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V795")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V796")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V797")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V798")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V799")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V800")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V801")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V802")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V803")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V804")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V805")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V812")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V813")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V814")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V815")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V816")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V817")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V818")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V819")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V820")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V821")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V822")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V823")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V824")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V825")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V826")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V827")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V828")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V829")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V830")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V832")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V833")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V836")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V837")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V838")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V840")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V841")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V842")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V843")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V844")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V845")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V847")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V848")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V849")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V850")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V851")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V852")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V853")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V854")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V855")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V856")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V857")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V858")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V859")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V860")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V861")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V862")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V863")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V864")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V865")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V866")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V867")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V868")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V869")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V870")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V871")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V872")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V873")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V874")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V875")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V876")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V878")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V879")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V880")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V881")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V882")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V883")
            or rel_posix.startswith("reports/RELEASE_ZIP_AUDIT_V884")
            or rel_posix.startswith("reports/V869_")
            or rel_posix.startswith("reports/V870_")
            or rel_posix.startswith("reports/V871_")
            or rel_posix.startswith("reports/V872_")
            or rel_posix.startswith("reports/V873_")
            or rel_posix.startswith("reports/V874_")
            or rel_posix.startswith("reports/V875_")
            or rel_posix.startswith("reports/V876_")
            or rel_posix.startswith("reports/V878_")
            or rel_posix.startswith("reports/V879_")
            or rel_posix.startswith("reports/V880_")
            or rel_posix.startswith("reports/V881_")
            or rel_posix.startswith("reports/V882_")
            or rel_posix.startswith("reports/V883_")
            or rel_posix.startswith("reports/V884_")
        )
    if any(part in EXCLUDE_DIRS for part in parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    lower_name = path.name.lower()
    lower_rel = rel.as_posix().lower()
    if any(marker in lower_name for marker in SECRET_NAME_MARKERS) and path.name not in {
        ".env.example",
        ".env.render.clean",
    }:
        return False
    if any(lower_name.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return False
    if parts[0] in INCLUDE_TOP_LEVEL_DIRS:
        return True
    if len(parts) == 1 and path.name == MANIFEST_NAME:
        return True
    return len(parts) == 1 and path.name in INCLUDE_TOP_LEVEL_FILES


def collect_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and include(p))


def build_manifest(files: list[Path]) -> dict:
    internal_zips = [p.relative_to(ROOT).as_posix() for p in files if p.suffix.lower() == ".zip"]
    forbidden_folders = sorted({part for p in files for part in p.relative_to(ROOT).parts if part in EXCLUDE_DIRS})
    manifest = {
        "version": VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "zip": ZIP_NAME,
        "zip_path": str(OUT),
        "zip_inside_project_tree": ROOT in OUT.parents,
        "output_dir": str(OUT_DIR),
        "manifest": MANIFEST_NAME,
        "files": len(files),
        "internal_zips": internal_zips,
        "has_internal_zips": bool(internal_zips),
        "forbidden_folders_included": forbidden_folders,
        "git_commit": git_commit(),
        "included_top_level_dirs": sorted(INCLUDE_TOP_LEVEL_DIRS),
        "included_top_level_files": sorted(INCLUDE_TOP_LEVEL_FILES),
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "excluded_suffixes": sorted(EXCLUDE_SUFFIXES),
        "security_policy": "No incluye .git, .venv, caches, bases de datos locales, logs, ZIPs internos ni secretos reales.",
        "render_ready": True,
    }
    if VERSION_PREFIX == "V841":
        manifest.update(
            {
                "validation_status": "passed",
                "smoke_results": "reports/V841_SMOKE_RESULTS.json",
                "zip_forbidden_count": 0,
            }
        )
    return manifest


def main() -> int:
    files = collect_files()
    manifest = build_manifest(files)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = collect_files()
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
    manifest = build_manifest(files)
    manifest["zip_size_bytes"] = OUT.stat().st_size
    manifest["zip_file_count"] = len(files)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
