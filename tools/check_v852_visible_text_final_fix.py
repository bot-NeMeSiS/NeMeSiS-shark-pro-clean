from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD = ["lo primo", "Result ados", "EspaÁa", "ESPAÃ", "Ã", "Â", "�", "undefined"]


def main():
    failures = []
    for path in list((ROOT / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for bad in BAD:
            if bad in text:
                failures.append(f"{path.relative_to(ROOT)}: {bad}")
    assert not failures, "\n".join(failures)
    assert "Hora España/Madrid" in (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    print("V852 visible text final fix OK")


if __name__ == "__main__":
    main()
