#!/usr/bin/env python3
"""
Check that the project version is consistent across pyproject.toml and
logerr/__init__.py.

There's no single source of truth for the version (setuptools reads
pyproject.toml, but the package's own __version__ attribute is a separate
literal string), so this script exists to catch the two from silently
drifting apart rather than trying to eliminate the duplication.
"""

import re
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def get_pyproject_version() -> str:
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    return data["project"]["version"]


def get_init_version() -> str:
    text = (PROJECT_ROOT / "logerr" / "__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise ValueError("Could not find __version__ in logerr/__init__.py")
    return match.group(1)


def main() -> None:
    versions = {
        "pyproject.toml": get_pyproject_version(),
        "logerr/__init__.py": get_init_version(),
    }

    unique_versions = set(versions.values())

    if len(unique_versions) == 1:
        print(f"✅ Version is in sync across all files: {unique_versions.pop()}")
        return

    print("❌ Version mismatch detected:")
    for source, version in versions.items():
        print(f"  {source}: {version}")
    sys.exit(1)


if __name__ == "__main__":
    main()
