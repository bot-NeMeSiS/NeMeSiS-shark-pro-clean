from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "templates/base.html",
    "templates/home.html",
    "templates/calendar.html",
    "templates/live.html",
    "templates/picks.html",
    "templates/shark.html",
    "templates/profile.html",
    "templates/telegram.html",
    "templates/support.html",
]
BAD = ["ESPAÃ", "EspaÁa", "Ã", "Â", "�", "lo primo", "undefined"]


def main():
    failures = []
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for bad in BAD:
            if bad in text:
                failures.append(f"{rel}: {bad}")
    assert not failures, "\n".join(failures)
    print("V851 brand text orthography OK")


if __name__ == "__main__":
    main()
