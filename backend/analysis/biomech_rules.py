from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class RuleThresholds:
    # Frontal-plane projection angle proxy cutoffs (deg)
    fppa_alert_deg: float = 8.0
    fppa_high_deg: float = 13.0
    # Dynamic valgus proxy (knee width / ankle width)
    valgus_ratio_alert: float = 0.85
    valgus_ratio_high: float = 0.75
    # Trunk lean cue (frontal lean to vertical)
    trunk_lean_alert_deg: float = 12.0
    trunk_lean_high_deg: float = 20.0
    # Symmetry and visibility
    symmetry_alert_deg: float = 10.0
    symmetry_high_deg: float = 16.0
    visibility_min: float = 0.55


TH = RuleThresholds()

# Reference tags are mapped to literature list in docs/biomechanics_reference.md
REFS = {
    "FPPA_CUTOFF": "IJSPT 2023 (FPPA cutoff about 8.2 deg)",
    "DV_HIGH": "AJSM 2025 (dynamic valgus high risk about 18-20 deg context)",
    "TRUNK_LEAN": "Clin Biomech 2012 (moderate trunk lean modulates ACL load)",
    "WBLT": "Manual Therapy 2015 + Scientific Reports 2021 (WBLT reliability and normative context)",
}


def analyze_biomech(metrics: Dict[str, float], action_label: str) -> Tuple[float, str, str, List[str]]:
    """Return severity [0,1], issue, cue, and reference tags used by triggered rules."""
    refs: List[str] = []
    severity = 0.0
    issue = "stable_motion"
    cue = "maintain alignment and controlled tempo"

    visibility = float(metrics.get("visibility", 0.0))
    if visibility < TH.visibility_min:
        return 0.0, "capture_quality_low", "step back and keep full body visible", refs

    fppa_proxy = float(metrics.get("fppa_proxy_deg", 0.0))
    valgus_ratio = float(metrics.get("valgus_ratio", 1.0))
    trunk_lean = float(metrics.get("trunk_lean_deg", 0.0))
    symmetry = float(metrics.get("symmetry", 0.0))

    if fppa_proxy > TH.fppa_alert_deg:
        severity += 0.2
        refs.append("FPPA_CUTOFF")
    if fppa_proxy > TH.fppa_high_deg:
        severity += 0.15

    if valgus_ratio < TH.valgus_ratio_alert:
        severity += 0.2
        refs.append("DV_HIGH")
        issue = "knee_valgus_risk"
        cue = "keep knee tracking over the second toe; control hip rotation"
    if valgus_ratio < TH.valgus_ratio_high:
        severity += 0.2

    if trunk_lean > TH.trunk_lean_alert_deg:
        severity += 0.12
        refs.append("TRUNK_LEAN")
    if trunk_lean > TH.trunk_lean_high_deg:
        severity += 0.13
        issue = "trunk_control_risk"
        cue = "stiffen core and reduce lateral trunk drift at impact"

    if symmetry > TH.symmetry_alert_deg:
        severity += 0.08
    if symmetry > TH.symmetry_high_deg:
        severity += 0.12
        issue = "asymmetry_risk"
        cue = "reduce side-to-side asymmetry before increasing speed"

    if action_label in {"shoot_like", "pass_like", "jump_like"} and (issue == "stable_motion"):
        cue = "good motion; keep ankle lock and balanced plant foot"

    severity = max(0.0, min(1.0, severity))
    if not refs:
        refs.append("WBLT")
    # Deduplicate while preserving order
    seen = set()
    refs = [r for r in refs if not (r in seen or seen.add(r))]
    return severity, issue, cue, refs
