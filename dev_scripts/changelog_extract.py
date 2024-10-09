import re
import sys
from pathlib import Path
from typing import Iterable

THIS_DIR = Path(__file__).parent
CHANGELOG = THIS_DIR.parent / "CHANGELOG.md"


def fetch_changes(changelog: Path, version: str) -> Iterable[str]:
    with open(changelog, "r") as f:
        lines = f.readlines()

    found_a_change = False
    aggregate = False
    for line in lines:
        if line.startswith(f"## {version}"):
            aggregate = True

        if aggregate:
            if line.startswith("-"):
                line = re.sub(r"-\s*", "", line).strip()
                found_a_change = True
                yield line
            elif found_a_change:
                aggregate = False

    return changes


version = sys.argv[1].strip()
changes = fetch_changes(CHANGELOG, version)
if not changes:
    exit(1)

for change in changes:
    print("- " + change)
