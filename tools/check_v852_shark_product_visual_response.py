from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert (ROOT / "engines" / "shark_ai_product_assistant_engine.py").exists()
    app_py = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "/api/shark/ask" in app_py
    assert "has_v845_shark_ai_product_assistant" in app_py
    print("V852 SHARK product visual response OK")


if __name__ == "__main__":
    main()
