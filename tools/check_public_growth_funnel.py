#!/usr/bin/env python3
"""Read-only public acquisition funnel smoke test. No account, payment or API writes.

Usage: python tools/check_public_growth_funnel.py --base-url https://example.com
Exit code 1 means one or more public paths failed; output is JSON for CI review.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


PATHS = ("/", "/registro", "/cliente-login", "/membresias", "/precios")
MAX_BYTES = 1_000_000
TIMEOUT_SECONDS = 10


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PageInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.forms = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "form":
            self.forms.append({"method": attrs.get("method", "get").lower(),
                               "action": attrs.get("action", "")})
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def inspect(base_url, path, opener):
    url = urljoin(base_url + "/", path.lstrip("/"))
    item = {"path": path, "status": None, "ok": False, "findings": []}
    try:
        response = opener.open(Request(url, headers={"User-Agent": "NeMeSiS-Public-Funnel-QA/1.0",
                                                      "Accept": "text/html"}), timeout=TIMEOUT_SECONDS)
    except HTTPError as error:
        response = error
    except (URLError, TimeoutError, OSError) as error:
        item["findings"].append("Network failure: " + type(error).__name__)
        return item

    with response:
        item["status"] = response.status
        redirect = response.headers.get("Location", "")
        if response.status in (301, 302, 303, 307, 308):
            destination = urljoin(url, redirect)
            if urlparse(destination).netloc != urlparse(base_url).netloc:
                item["findings"].append("External redirect; manual review needed")
            else:
                item["findings"].append("Internal redirect to " + urlparse(destination).path)
            return item
        if response.status != 200:
            item["findings"].append("Unexpected HTTP status")
            return item
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            item["findings"].append("HTML exceeds inspection limit")
            return item
        parser = PageInspector()
        parser.feed(data.decode("utf-8", errors="replace"))
        item["title"] = parser.title.strip()[:160]
        item["forms"] = len(parser.forms)
        if not parser.title.strip():
            item["findings"].append("Missing HTML title")
        if path == "/":
            targets = ("/registro", "/membresias", "/precios", "/cliente-login")
            item["has_acquisition_cta"] = any(
                urlparse(urljoin(url, link)).path in targets for link in parser.links
            )
            if not item["has_acquisition_cta"]:
                item["findings"].append("No direct registration/pricing/login link")
        if path == "/registro" and not parser.forms:
            item["findings"].append("No registration form detected")
        if path in ("/membresias", "/precios"):
            item["has_registration_path"] = any(
                urlparse(urljoin(url, link)).path in ("/registro", "/cliente-login", "/comprar/PRO", "/comprar/ELITE")
                for link in parser.links
            ) or any("/pagos/checkout/" in form["action"] for form in parser.forms)
            if not item["has_registration_path"]:
                item["findings"].append("No visible signup or checkout path")
        # Detect obvious error pages; never collect form values or private data.
        if re.search(r"(?i)(traceback \(most recent call last\)|internal server error)", data.decode("utf-8", "replace")):
            item["findings"].append("Potential error/debug text")
        item["ok"] = not item["findings"]
        return item


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True, help="Your deployment base URL (HTTPS recommended)")
    args = ap.parse_args(argv)
    parsed = urlparse(args.base_url.strip())
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
        ap.error("Use an absolute http(s) URL without embedded credentials")
    base_url = args.base_url.rstrip("/")
    opener = build_opener(NoRedirect())
    results = [inspect(base_url, path, opener) for path in PATHS]
    output = {"base_url": base_url, "read_only": True, "checked": len(results),
              "passed": sum(bool(row["ok"]) for row in results),
              "results": results}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["passed"] == output["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
