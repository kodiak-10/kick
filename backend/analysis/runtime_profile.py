from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, List

import json
import numpy as np


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RuntimeProfiler:
    label: str = "live"
    durations: DefaultDict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    durations_by_scope: DefaultDict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    gate_counts: DefaultDict[str, int] = field(default_factory=lambda: defaultdict(int))
    score_counts: DefaultDict[str, int] = field(default_factory=lambda: defaultdict(int))
    frame_count: int = 0
    analyzed_count: int = 0
    started_at: str = field(default_factory=_now_iso)

    def record(self, name: str, duration_s: float, flow_stage: str = "unknown", phase: str = "unknown"):
        val = float(duration_s)
        self.durations[name].append(val)
        self.durations_by_scope[f"{flow_stage}|{name}"].append(val)
        self.durations_by_scope[f"{flow_stage}|{phase}|{name}"].append(val)

    def record_frame(self):
        self.frame_count += 1

    def record_analysis(self):
        self.analyzed_count += 1

    def record_gate(self, reason: str, scored: bool):
        self.gate_counts[str(reason)] += 1
        self.score_counts["scored" if scored else "withheld"] += 1

    def _summarize(self, values: List[float]) -> Dict[str, float]:
        arr = np.asarray(values, dtype=np.float64)
        return {
            "count": int(arr.size),
            "mean_ms": float(arr.mean() * 1000.0),
            "max_ms": float(arr.max() * 1000.0),
            "p95_ms": float(np.percentile(arr, 95) * 1000.0),
        }

    def build_report(self) -> Dict[str, object]:
        stage_metrics = {name: self._summarize(values) for name, values in self.durations.items() if values}
        scope_metrics = {name: self._summarize(values) for name, values in self.durations_by_scope.items() if values}
        bottlenecks = sorted(
            (
                {"stage": name, **summary}
                for name, summary in stage_metrics.items()
            ),
            key=lambda item: (-item["p95_ms"], -item["mean_ms"]),
        )
        total_gate = sum(self.gate_counts.values()) or 1
        gate_distribution = {
            key: {
                "count": int(val),
                "ratio": float(val / total_gate),
            }
            for key, val in sorted(self.gate_counts.items(), key=lambda item: (-item[1], item[0]))
        }
        total_scored = sum(self.score_counts.values()) or 1
        return {
            "label": self.label,
            "generated_at": _now_iso(),
            "started_at": self.started_at,
            "frame_count": int(self.frame_count),
            "analyzed_count": int(self.analyzed_count),
            "stage_metrics": stage_metrics,
            "scope_metrics": scope_metrics,
            "bottlenecks": bottlenecks[:12],
            "gate_distribution": gate_distribution,
            "score_distribution": {
                key: {
                    "count": int(val),
                    "ratio": float(val / total_scored),
                }
                for key, val in self.score_counts.items()
            },
        }

    def save(self, path: str | Path) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.build_report(), ensure_ascii=False, indent=2))
        return str(out)
