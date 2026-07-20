#!/usr/bin/env python3
"""Non-destructive regression and benchmark for the V937 SHARK hotfix."""
from __future__ import annotations

import importlib
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V937_VERSION = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
V938_VERSION = "V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_FINAL"
SUPPORTED_VERSIONS = {V937_VERSION, V938_VERSION}
RUNS = 10


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return ordered[index]


def prepare_db(target: Path) -> None:
    source = ROOT / "data" / "database.db"
    if source.exists() and source.stat().st_size:
        shutil.copy2(source, target)


def load_app(db_path: Path):
    os.environ["DB_PATH"] = str(db_path)
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    os.environ["OPENAI_API_KEY"] = ""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("app")


def run() -> dict:
    current_version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    require(current_version in SUPPORTED_VERSIONS, "VERSION.txt no conserva V937 ni su sucesora V938")
    app_source = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    require("v932_safe_dashboard_data(request.path, compact=True)" in app_source, "SHARK no usa contexto compacto")
    require("prebuilt_briefing=briefing" in app_source, "SHARK reconstruye el briefing")
    require("prebuilt_provider_state=provider_state" in app_source, "SHARK repite el diagnostico del proveedor")
    require("X-Nemesis-Shark-Data" in app_source, "Faltan metricas seguras de SHARK")

    original_env = dict(os.environ)
    try:
        with tempfile.TemporaryDirectory(prefix="nemesis-v937-shark-") as temp_dir:
            db_path = Path(temp_dir) / "shark-profile.db"
            prepare_db(db_path)
            module = load_app(db_path)
            module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)

            external_calls: list[str] = []
            page_memory_writes: list[str] = []
            original_urlopen = urllib.request.urlopen
            original_rows = module.rows
            query_counter = {"count": 0}

            def blocked_urlopen(*args, **kwargs):
                external_calls.append(type(args[0]).__name__ if args else "request")
                raise RuntimeError("external_call_blocked_in_shark_test")

            def counted_rows(query, params=()):
                query_counter["count"] += 1
                return original_rows(query, params)

            urllib.request.urlopen = blocked_urlopen
            module.rows = counted_rows
            module.save_shark_context = lambda *args, **kwargs: page_memory_writes.append("write")

            client = module.app.test_client()
            warmup = client.get("/shark")
            require(warmup.status_code == 200, "Warmup SHARK no devuelve 200")
            module.invalidate_v934_realtime_cache("v934:sports:public-summary")

            samples: list[float] = []
            query_counts: list[int] = []
            responses = []
            for _ in range(RUNS):
                before_queries = query_counter["count"]
                started = time.perf_counter()
                response = client.get("/shark")
                samples.append((time.perf_counter() - started) * 1000.0)
                query_counts.append(query_counter["count"] - before_queries)
                responses.append(response)

            cold_ms = samples[0]
            hot_samples = samples[1:]
            hot_median = statistics.median(hot_samples)
            p95_ms = percentile_95(samples)
            require(all(response.status_code == 200 for response in responses), "SHARK devuelve un status distinto de 200")
            require(cold_ms < 4000, f"Cache fria SHARK supera 4 s: {cold_ms:.1f} ms")
            require(hot_median < 1500, f"Cache caliente SHARK supera 1.5 s: {hot_median:.1f} ms")
            require(p95_ms < 2500, f"p95 SHARK supera 2.5 s: {p95_ms:.1f} ms")
            require(max(query_counts[1:]) <= 20, f"Demasiadas lecturas SQL por cache hit: {max(query_counts[1:])}")
            require(not external_calls, f"SHARK intento llamadas externas durante render: {len(external_calls)}")
            require(not page_memory_writes, "GET /shark intento escribir memoria SHARK")

            first = responses[0]
            last = responses[-1]
            require(first.headers.get("X-Nemesis-Shark-Data") == "db-cache-only", "Falta guard DB/cache-only")
            require(first.headers.get("X-Nemesis-Shark-Cache") == "refreshed", "La prueba fria no refresco cache")
            require(last.headers.get("X-Nemesis-Shark-Cache") == "hit", "La prueba caliente no reutilizo cache")
            require("shark_sports_context;dur=" in (last.headers.get("Server-Timing") or ""), "Faltan fases Server-Timing")
            require(b"SHARK" in last.data and b"v933-shark-page" in last.data, "La UI SHARK no se conserva")

            risk = client.get("/shark?q=riesgo")
            require(risk.status_code == 200 and b"Riesgo" in risk.data, "La pregunta rapida de riesgo no funciona")

            original_provider_status = module.get_api_sports_status
            module.get_api_sports_status = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider_down"))
            module.invalidate_v934_realtime_cache("v934:sports:public-summary")
            provider_down_started = time.perf_counter()
            provider_down = client.get("/shark")
            provider_down_ms = (time.perf_counter() - provider_down_started) * 1000.0
            module.get_api_sports_status = original_provider_status
            require(provider_down.status_code == 200, "Proveedor caido provoca error en SHARK")
            require(provider_down_ms < 4000, f"Fallback de proveedor supera 4 s: {provider_down_ms:.1f} ms")

            empty_db = Path(temp_dir) / "shark-empty.db"
            module.DB_PATH = str(empty_db)
            module._SEEDED_DB_PATH = None
            module._SEEDING_DB_PATH = None
            module.APP_INITIALIZED = False
            module.invalidate_v934_realtime_cache()
            empty_client = module.app.test_client()
            empty_started = time.perf_counter()
            empty_response = empty_client.get("/shark")
            empty_ms = (time.perf_counter() - empty_started) * 1000.0
            require(empty_response.status_code == 200, "DB vacia provoca error en SHARK")
            require(empty_ms < 4000, f"Fallback con DB vacia supera 4 s: {empty_ms:.1f} ms")
            require(b"SHARK" in empty_response.data, "DB vacia pierde la experiencia SHARK")

            urllib.request.urlopen = original_urlopen

            return {
                "ok": True,
                "version": current_version,
                "runs": RUNS,
                "status_codes": sorted({response.status_code for response in responses}),
                "cold_cache_ms": round(cold_ms, 1),
                "hot_cache_median_ms": round(hot_median, 1),
                "median_ms": round(statistics.median(samples), 1),
                "p95_ms": round(p95_ms, 1),
                "min_ms": round(min(samples), 1),
                "max_ms": round(max(samples), 1),
                "query_count_cold": query_counts[0],
                "query_count_hot_max": max(query_counts[1:]),
                "external_calls": len(external_calls),
                "page_memory_writes": len(page_memory_writes),
                "provider_down_ms": round(provider_down_ms, 1),
                "empty_db_ms": round(empty_ms, 1),
                "response_bytes": len(last.data),
                "server_timing": last.headers.get("Server-Timing") or "",
            }
    finally:
        os.environ.clear()
        os.environ.update(original_env)


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=True, indent=2))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=True, indent=2))
        raise SystemExit(1)
