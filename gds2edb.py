"""Repository-root launcher that forwards to src/gds2edb/gds2edb.py."""

from pathlib import Path
import runpy


def main() -> int:
    project_root = Path(__file__).resolve().parent
    entry = project_root / "src" / "gds2edb" / "gds2edb.py"
    if not entry.exists():
        raise FileNotFoundError(f"Entry file not found: {entry}")

    runpy.run_path(str(entry), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
