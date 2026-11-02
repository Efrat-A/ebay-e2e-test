from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def load_config(profile: str | None = None) -> dict[str, Any]:
    raw = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    name = profile or os.getenv("ENV_PROFILE") or raw["default_profile"]
    if name not in raw["profiles"]:
        raise ValueError(f"Unknown profile '{name}'. Available: {list(raw['profiles'])}")
    cfg = dict(raw["profiles"][name])
    cfg["profile"] = name
    # Env vars override file values (handy in CI)
    if os.getenv("HEADLESS") is not None:
        cfg["headless"] = os.getenv("HEADLESS", "").lower() in ("1", "true", "yes")
    if os.getenv("BROWSER"):
        cfg["browser"] = os.environ["BROWSER"]
    cfg["credentials"] = {
        "username": os.getenv("EBAY_USERNAME"),
        "password": os.getenv("EBAY_PASSWORD"),
    }
    return cfg


def load_scenarios(path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(path) if path else ROOT / "data" / "test_data.json"
    return json.loads(path.read_text(encoding="utf-8"))["scenarios"]
