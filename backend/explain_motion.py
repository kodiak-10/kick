#!/usr/bin/env python3
"""Explain motion faults with rules + lightweight classifier.
Disclaimer: Research prototype, not medical advice.
"""

import argparse
import json
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "models" / "cause_classifier.pt"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _load_or_train_model():
    try:
        import joblib
        if MODEL_PATH.exists():
            return joblib.load(MODEL_PATH)
    except Exception:
        pass

    # Train a tiny synthetic classifier as fallback
    try:
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline

        X = np.random.randn(200, 10)
        y = np.random.randint(0, 3, size=(200,))
        clf = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(16,), max_iter=300))
        clf.fit(X, y)

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            import joblib
            joblib.dump(clf, MODEL_PATH)
        except Exception:
            pass
        return clf
    except Exception:
        return None


def _rule_based(joints, kinetics):
    faults = []
    # Simple heuristic rules
    knee_angle = np.array(joints.get("knee_angle", []))
    hip_angle = np.array(joints.get("hip_angle", []))
    if knee_angle.size and knee_angle.min() < 70:
        faults.append(("too_deep_squat", 0.7, "Knee angle frequently below 70 degrees"))
    if hip_angle.size and hip_angle.mean() < 120:
        faults.append(("excessive_forward_lean", 0.6, "Hip angle suggests forward lean"))

    if not faults:
        faults.append(("no_clear_fault", 0.3, "No strong rule-based fault detected"))
    return faults


def _mlp_score(model, joints, kinetics):
    if model is None:
        return [("unknown", 0.2, "Model unavailable")]

    # Create simple feature vector
    feats = []
    for k in ("knee_angle", "hip_angle", "elbow_angle", "ankle_angle"):
        arr = np.array(joints.get(k, []))
        feats.extend([
            float(arr.mean()) if arr.size else 0.0,
            float(arr.min()) if arr.size else 0.0,
            float(arr.max()) if arr.size else 0.0,
        ])
    feats = np.array(feats, dtype=np.float32).reshape(1, -1)

    try:
        probs = model.predict_proba(feats)[0]
        labels = ["mobility", "stability", "technique"]
        ranked = sorted(zip(labels, probs), key=lambda x: -x[1])
        return [(name, float(p), "MLP likelihood") for name, p in ranked]
    except Exception:
        return [("unknown", 0.2, "Model inference failed")]


def explain(clip_id, joints, kinetics):
    model = _load_or_train_model()
    rules = _rule_based(joints, kinetics)
    mlp = _mlp_score(model, joints, kinetics)

    causes = []
    for name, prob, rationale in rules[:2] + mlp[:2]:
        causes.append({"name": name, "prob": round(prob, 3), "short_rationale": rationale})

    suggested = []
    if any(c["name"] == "too_deep_squat" for c in causes):
        suggested.append({"id": "box_squat", "name": "Box Squat", "reason": "Control depth and knee alignment"})
    if any(c["name"] == "excessive_forward_lean" for c in causes):
        suggested.append({"id": "goblet_squat", "name": "Goblet Squat", "reason": "Encourages upright torso"})
    if not suggested:
        suggested.append({"id": "tempo_squat", "name": "Tempo Squat", "reason": "Improve control and awareness"})

    result = {
        "fault_label": causes[0]["name"] if causes else "unknown",
        "causes": causes,
        "suggested_exercises": suggested,
        "disclaimer": "Research prototype, not medical advice.",
    }
    return result


def explain_report(clip_id, output_json):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = REPORTS_DIR / f"explain_{clip_id}.pdf"

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, f"Explain Report: {clip_id}")
        y = 690
        for line in output_json.splitlines():
            c.drawString(72, y, line[:90])
            y -= 14
            if y < 80:
                c.showPage()
                y = 720
        c.showPage()
        c.save()
    except Exception:
        # Minimal PDF fallback
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 720 Td (Report) Tj ET\nendstream endobj\ntrailer<</Root 1 0 R>>\n%%EOF")

    return pdf_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("joints_time_series")
    ap.add_argument("kinetics_time_series")
    args = ap.parse_args()

    joints = json.loads(Path(args.joints_time_series).read_text())
    kinetics = json.loads(Path(args.kinetics_time_series).read_text())

    result = explain(args.clip_id, joints, kinetics)
    out_path = Path(f"explain_{args.clip_id}.json")
    out_path.write_text(json.dumps(result, indent=2))

    pdf = explain_report(args.clip_id, json.dumps(result, indent=2))
    print(f"Saved: {out_path}")
    print(f"Saved: {pdf}")


if __name__ == "__main__":
    main()
