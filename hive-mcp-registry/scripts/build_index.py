#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SERVERS_DIR = REPO_ROOT / "registry" / "servers"
INDEX_PATH = REPO_ROOT / "registry_index.json"


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    manifests = [load_manifest(path) for path in sorted(SERVERS_DIR.glob("*/manifest.json"))]
    manifests.sort(key=lambda item: item["name"])

    payload = {
        "version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "servers": manifests,
    }

    with INDEX_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    print(f"Built index with {len(manifests)} servers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
