"""Package clean production source files into a ZIP archive.

Excludes virtual environments, .git, .env secrets, __pycache__, and temporary files.
"""
import os
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_ZIP = ROOT_DIR / "smart-inventory-intelligence-source.zip"

EXCLUDE_DIRS = {
    ".git",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".vscode",
    ".idea",
}

EXCLUDE_FILES = {
    ".env",
    ".env.local",
    "smart-inventory-intelligence-source.zip",
    "Thumbs.db",
    ".DS_Store",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".zip",
    ".log",
}


def should_include(path: Path) -> bool:
    rel_path = path.relative_to(ROOT_DIR)
    parts = set(rel_path.parts)

    # Check directory exclusion
    if parts.intersection(EXCLUDE_DIRS):
        return False

    # Check file exclusion
    if path.name in EXCLUDE_FILES or path.name.startswith(".env."):
        return False

    # Check extension exclusion
    if path.suffix in EXCLUDE_EXTENSIONS:
        return False

    return True


def package():
    print(f"Packaging source repository: {ROOT_DIR}")
    included_files = []

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                file_path = Path(root) / file
                if should_include(file_path):
                    rel_path = file_path.relative_to(ROOT_DIR)
                    zf.write(file_path, arcname=str(rel_path))
                    included_files.append(str(rel_path))

    print(f"Successfully created: {OUTPUT_ZIP}")
    print(f"Total files included: {len(included_files)}")
    return included_files


if __name__ == "__main__":
    package()
