from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CRITICAL_FILES = [
    "VERSION.txt",
    "APP_VERSION",
    "templates/base.html",
    "templates/home.html",
    "templates/index.html",
    "templates/landing.html",
    "templates/public_home.html",
    "static/app.css",
    "app.py",
]
COMMON_MOJIBAKE = ["Ã", "Â", "�", "ï¿½", "Ãƒ", "Ã‚"]
VISIBLE_BAD_WORDS = re.compile(r">\s*(None|null|undefined)\s*<", re.IGNORECASE)
VISIBLE_RN = re.compile(r"(?i)(NeMeSiS\s+SHARK\s+PRO\s+rn\b|\brn\s+rn\b|`r`n|\\\\r\\\\n)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_script_style(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.I | re.S)
    return html


def visible_text(html: str) -> str:
    cleaned = strip_script_style(html)
    cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def template_starts_clean(rel: str, text: str) -> bool:
    trimmed = text.lstrip("\ufeff\r\n\t ")
    if rel == "templates/base.html":
        return trimmed.lower().startswith("<!doctype html") or trimmed.lower().startswith("<html")
    if rel.startswith("templates/"):
        return not trimmed.lower().startswith("rn")
    return True


def collect_failures() -> list[str]:
    failures: list[str] = []
    for rel in CRITICAL_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        if raw.startswith(b"\xef\xbb\xbf"):
            failures.append(f"{rel} has UTF-8 BOM")
        if "\ufeff" in text:
            failures.append(f"{rel} contains visible BOM marker")
        if not template_starts_clean(rel, text):
            failures.append(f"{rel} starts with visible garbage before HTML/template content")
        if rel.startswith("templates/") and VISIBLE_RN.search(visible_text(text)[:2500]):
            failures.append(f"{rel} contains visible rn artifact")
        if rel in {"templates/base.html", "templates/home.html"} and VISIBLE_BAD_WORDS.search(strip_script_style(text)):
            failures.append(f"{rel} contains visible None/null/undefined")
        if rel.startswith("templates/") and any(token in visible_text(text)[:2500] for token in COMMON_MOJIBAKE):
            failures.append(f"{rel} contains common mojibake near visible top")
    return failures


def main() -> int:
    failures = collect_failures()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        import app as app_module

        app_module.app.testing = True
        client = app_module.app.test_client()
        response = client.get("/")
        html = response.get_data(as_text=True)
        text = visible_text(html)
        if response.status_code != 200:
            failures.append(f"/ returned {response.status_code}")
        if html.startswith("\ufeff") or "\ufeff" in html[:200]:
            failures.append("/ contains visible BOM near start")
        if not html.lstrip("\ufeff\r\n\t ").lower().startswith("<!doctype html"):
            failures.append("/ does not start with clean doctype")
        if VISIBLE_RN.search(text[:2500]):
            failures.append("/ contains visible rn artifact")
        if VISIBLE_BAD_WORDS.search(strip_script_style(html)) or re.search(r"\b(None|null|undefined)\b", text[:2500], re.I):
            failures.append("/ contains visible None/null/undefined near top")
        if any(token in text[:2500] for token in COMMON_MOJIBAKE):
            failures.append("/ contains common mojibake near top")
    except Exception as exc:
        failures.append(f"home render unavailable: {exc}")

    if failures:
        print("visible artifact check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("visible artifact check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
