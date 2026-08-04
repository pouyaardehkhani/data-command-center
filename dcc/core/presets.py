"""Generic per-feature preset save/load/delete, storing a settings dataclass
as JSON under %APPDATA%/DataCommandCenter/presets/<feature>/<name>.json."""
from __future__ import annotations

import dataclasses
import json
import re

from dcc.paths import presets_dir


def _safe_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    return name or "preset"


def feature_dir(feature: str):
    d = presets_dir() / feature
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_presets(feature: str) -> list:
    d = feature_dir(feature)
    return sorted(p.stem for p in d.glob("*.json"))


def save_preset(feature: str, name: str, data) -> None:
    if dataclasses.is_dataclass(data):
        payload = dataclasses.asdict(data)
    else:
        payload = data
    path = feature_dir(feature) / f"{_safe_name(name)}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_preset(feature: str, name: str) -> dict:
    path = feature_dir(feature) / f"{_safe_name(name)}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def delete_preset(feature: str, name: str) -> None:
    path = feature_dir(feature) / f"{_safe_name(name)}.json"
    if path.exists():
        path.unlink()
