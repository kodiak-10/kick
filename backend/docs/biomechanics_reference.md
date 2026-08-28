# Biomechanics Reference Notes (for `soccer_basic` rules)

These thresholds are used as practical screening cues for monocular 2D tracking. They are **not** medical diagnosis thresholds.

## Rule-to-reference mapping

1. `FPPA_CUTOFF`
- Source: International Journal of Sports Physical Therapy (PFP discrimination study)
- Finding used: FPPA cutoff around `8.2 deg` as a practical alert level for frontal-plane knee collapse screening.
- URL: https://ijspt.scholasticahq.com/article/74269

2. `DV_HIGH`
- Source: J ISAKOS 2025, prospective ACLR follow-up study
- Finding used: dynamic valgus around `18-20 deg` associated with higher graft rerupture risk in the reported cohort.
- URL: https://pubmed.ncbi.nlm.nih.gov/41241203/

3. `TRUNK_LEAN`
- Source: Clin Biomech 2008 (Blackburn & Padua)
- Finding used: trunk position materially changes hip/knee kinematics during landing; trunk strategy is a key injury-risk modifier.
- URL: https://pubmed.ncbi.nlm.nih.gov/18037546/

4. `WBLT`
- Source: Manual Therapy 2015 systematic review (Powden et al.)
- Finding used: WBLT is reliable; MDC roughly 4.6-4.7 deg / 1.6-1.9 cm, used as measurement reliability context.
- URL: https://pubmed.ncbi.nlm.nih.gov/25704110/

## How these are applied in code
- File: `analysis/biomech_rules.py`
- Metrics are 2D proxies:
  - `fppa_proxy_deg`
  - `valgus_ratio`
  - `trunk_lean_deg`
  - `symmetry`
  - `visibility`
- Output:
  - `severity` (0-1)
  - `issue` label
  - `cue` (actionable coaching text)
  - `reference tags`

## Important limitation
- Monocular pose estimation cannot recover full 3D joint mechanics or internal loads.
- Use these outputs for coaching feedback and trend tracking, not medical diagnosis.
