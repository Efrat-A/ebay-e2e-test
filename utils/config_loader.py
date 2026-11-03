from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_profile(profiles: dict, name: str, seen: tuple = ()) -> dict:
    if name not in profiles:
        raise ValueError(f"Unknown profile '{name}'. Available: {list(profiles)}")
    if name in seen:
        raise ValueError(f"Circular 'extends' in profiles: {' -> '.join(seen + (name,))}")
    profile = dict(profiles[name])
    parent = profile.pop("extends", None)
    return _deep_merge(_resolve_profile(profiles, parent, seen + (name,)), profile) if parent else profile


def load_config(profile: str | None = None) -> dict[str, Any]:
    raw = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    name = profile or os.getenv("ENV_PROFILE") or raw["default_profile"]
    cfg = _resolve_profile(raw["profiles"], name)
    cfg["profile"] = name
    # Env vars override file values (handy in CI)
    if os.getenv("BROWSER"):
        cfg["browser"] = os.environ["BROWSER"]
    if os.getenv("SKIP_ON_BOT_PROTECTION"):
        cfg["skip_on_bot_protection"] = os.environ["SKIP_ON_BOT_PROTECTION"].strip().lower() in ("1", "true", "yes")
    cfg["credentials"] = {
        "username": os.getenv("EBAY_USERNAME"),
        "password": os.getenv("EBAY_PASSWORD"),
    }
    return cfg


def load_scenarios(path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(path) if path else ROOT / "data" / "test_data.json"
    return json.loads(path.read_text(encoding="utf-8"))["scenarios"]
