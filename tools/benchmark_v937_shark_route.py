#!/usr/bin/env python3
"""Measure GET /shark against the working tree or an exact Git revision."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import types
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = 10


def percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return ordered[index]


def prepare_db(target: Path) -> None:
    source = ROOT / "data" / "database.db"
    if source.exists() and source.stat().st_size:
        shutil.copy2(source, target)


def load_app(db_path: Path, source_ref: str):
    os.environ["DB_PATH"] = str(db_path)
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    os.environ["OPENAI_API_KEY"] = ""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if not source_ref:
        return importlib.import_module("app")

    source = subprocess.check_output(
        ["git", "show", f"{source_ref}:app.py"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    module_name = f"app_v937_benchmark_{source_ref[:10].replace('-', '_')}"
    module = types.ModuleType(module_name)
    module.__file__ = str(ROOT / "app.py")
    module.__package__ = ""
    sys.modules[module_name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def benchmark(source_ref: str, runs: int) -> dict:
    original_env = dict(os.environ)
    original_urlopen = urllib.request.urlopen
    try:
        with tempfile.TemporaryDirectory(prefix="nemesis-v937-shark-before-after-") as temp_dir:
            db_path = Path(temp_dir) / "benchmark.db"
            prepare_db(db_path)
            module = load_app(db_path, source_ref)
            module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)

            original_rows = module.rows
            original_save = module.save_shark_context
            query_counter = {"count": 0}
            external_calls: list[str] = []
            page_writes: list[str] = []

            def counted_rows(query, params=()):
                query_counter["count"] += 1
                return original_rows(query, params)

            def blocked_urlopen(*args, **kwargs):
                external_calls.append(type(args[0]).__name__ if args else "request")
                raise RuntimeError("external_call_blocked_in_benchmark")

            def counted_save(*args, **kwargs):
                page_writes.append("write")
                return original_save(*args, **kwargs)

            module.rows = counted_rows
            module.save_shark_context = counted_save
            urllib.request.urlopen = blocked_urlopen
            client = module.app.test_client()
            warmup = client.get("/shark")
            if hasattr(module, "invalidate_v934_realtime_cache"):
                module.invalidate_v934_realtime_cache("v934:sports:public-summary")
            query_counter["count"] = 0
            external_calls.clear()
            page_writes.clear()

            samples: list[float] = []
            query_counts: list[int] = []
            responses = []
            for _ in range(runs):
                before_queries = query_counter["count"]
                started = time.perf_counter()
                response = client.get("/shark")
                samples.append((time.perf_counter() - started) * 1000.0)
                query_counts.append(query_counter["count"] - before_queries)
                responses.append(response)

            return {
                "source": source_ref or "working_tree",
                "runs": runs,
                "warmup_status": warmup.status_code,
                "status_codes": sorted({response.status_code for response in responses}),
                "cold_cache_ms": round(samples[0], 1),
                "hot_cache_median_ms": round(statistics.median(samples[1:]), 1),
                "median_ms": round(statistics.median(samples), 1),
                "p95_ms": round(percentile_95(samples), 1),
                "min_ms": round(min(samples), 1),
                "max_ms": round(max(samples), 1),
                "query_count_cold": query_counts[0],
                "query_count_hot_max": max(query_counts[1:]),
                "external_calls": len(external_calls),
                "page_memory_writes": len(page_writes),
                "response_bytes": len(responses[-1].data),
                "server_timing": responses[-1].headers.get("Server-Timing") or "",
            }
    finally:
        urllib.request.urlopen = original_urlopen
        os.environ.clear()
        os.environ.update(original_env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", default="")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.source_ref, max(2, args.runs)), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
