from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_RULES_FILENAME = "kick_ai_football_thresholds_v1.json"
DEFAULT_RULES_PATH = Path(__file__).resolve().parent / DEFAULT_RULES_FILENAME

_ACTION_ALIASES = {
    "pass_like": "short_pass",
    "shoot_like": "shot_instep",
    "shot_like": "shot_instep",
    "first_touch_like": "receive_control",
    "pass_receive_sequence_like": "pass_receive_sequence",
    "dribble_like": "dribble_change_direction",
    "juggle_like": "juggling",
}


class RulesLoaderError(ValueError):
    pass


def _normalize_path(path: str | Path) -> str:
    return str(Path(path).resolve())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RulesLoaderError(message)


def resolve_action_name(action_name: str, rules: Optional[Dict[str, Any]] = None) -> str:
    rules = rules or load_football_rules()
    actions = rules.get("actions", {})
    normalized = str(action_name).strip()
    if normalized in actions:
        return normalized

    lowered = normalized.lower()
    if lowered in actions:
        return lowered

    alias = _ACTION_ALIASES.get(normalized) or _ACTION_ALIASES.get(lowered)
    if alias and alias in actions:
        return alias

    raise RulesLoaderError(
        f"unknown action '{action_name}'. available actions: {', '.join(sorted(actions.keys()))}"
    )


def _validate_metric_block(action_name: str, metric_name: str, metric_cfg: Dict[str, Any]) -> None:
    _require(isinstance(metric_cfg, dict), f"{action_name}.{metric_name} must be an object")
    _require("source_class" in metric_cfg, f"{action_name}.{metric_name} must include source_class")
    # `source_class == "product_default"` means the threshold is an engineering seed value
    # for Kick AI's single-camera pipeline. It is not a universal paper standard and
    # should be recalibrated with project-specific data over time.


def _validate_action_block(action_name: str, action_cfg: Dict[str, Any]) -> None:
    _require(isinstance(action_cfg, dict), f"actions.{action_name} must be an object")
    _require("display_name" in action_cfg, f"actions.{action_name} must include display_name")
    _require("primary_metrics" in action_cfg, f"actions.{action_name} must include primary_metrics")
    _require(isinstance(action_cfg.get("primary_metrics"), dict), f"actions.{action_name}.primary_metrics must be an object")
    for metric_name, metric_cfg in action_cfg["primary_metrics"].items():
        _validate_metric_block(action_name, metric_name, metric_cfg)
    for metric_name, metric_cfg in (action_cfg.get("secondary_metrics") or {}).items():
        _validate_metric_block(action_name, metric_name, metric_cfg)


def _validate_rules(payload: Dict[str, Any]) -> None:
    _require(isinstance(payload, dict), "rules file must contain a JSON object")
    _require("meta" in payload, "rules file missing meta")
    _require("global_quality_gate" in payload, "rules file missing global_quality_gate")
    _require("actions" in payload, "rules file missing actions")
    _require(isinstance(payload.get("global_quality_gate"), dict), "global_quality_gate must be an object")
    _require(isinstance(payload.get("actions"), dict), "actions must be an object")
    for action_name, action_cfg in payload["actions"].items():
        _validate_action_block(action_name, action_cfg)


@lru_cache(maxsize=4)
def _load_rules_cached(path_str: str) -> Dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        raise RulesLoaderError(f"rules file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    _validate_rules(payload)
    return payload


def load_football_rules(path: str | Path | None = None, *, refresh: bool = False) -> Dict[str, Any]:
    rule_path = Path(path) if path is not None else DEFAULT_RULES_PATH
    if refresh:
        _load_rules_cached.cache_clear()
    return copy.deepcopy(_load_rules_cached(_normalize_path(rule_path)))


def get_global_quality_gate(rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rules = rules or load_football_rules()
    return dict(rules["global_quality_gate"])


def get_action_rules(action_name: str, rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rules = rules or load_football_rules()
    actions = rules.get("actions", {})
    resolved = resolve_action_name(action_name, rules)
    if resolved not in actions:
        available = ", ".join(sorted(actions.keys()))
        raise RulesLoaderError(f"unknown action '{action_name}'. available actions: {available}")
    action_cfg = dict(actions[resolved])
    action_cfg["action_key"] = resolved
    action_cfg["input_action_name"] = action_name
    return action_cfg


def list_action_names(rules: Optional[Dict[str, Any]] = None) -> list[str]:
    rules = rules or load_football_rules()
    return sorted(rules.get("actions", {}).keys())
