from analysis.runtime_profile import RuntimeProfiler


def test_runtime_profiler_builds_bottleneck_report():
    profiler = RuntimeProfiler(label="unit")
    profiler.record_frame()
    profiler.record_analysis()
    profiler.record("pose_infer", 0.010, "active", "support")
    profiler.record("pose_infer", 0.012, "active", "contact")
    profiler.record("ui_render", 0.020, "active", "support")
    profiler.record_gate("ready", True)
    profiler.record_gate("ball_unstable", False)

    report = profiler.build_report()

    assert report["frame_count"] == 1
    assert report["analyzed_count"] == 1
    assert "pose_infer" in report["stage_metrics"]
    assert report["bottlenecks"][0]["stage"] == "ui_render"
    assert "ball_unstable" in report["gate_distribution"]
