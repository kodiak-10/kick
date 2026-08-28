from fastapi.testclient import TestClient

import main
from analysis import shot_analysis


def test_generate_plan():
    client = TestClient(main.app)
    payload = {
        "user_profile": {"age": 30},
        "explain_output": {"fault_label": "knee_valgus"},
        "goals": {"focus": "strength"},
    }
    r = client.post("/generate_plan", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "plan" in data
    assert "weeks" in data["plan"]


def test_health_endpoint():
    client = TestClient(main.app)

    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "analysis_backend"
    assert data["host"]
    assert isinstance(data["port"], int)
    assert "version" in data
    assert "analyzer_availability" in data
    assert "startup_warnings" in data


def test_analyze_video_endpoint(monkeypatch, tmp_path, capsys):
    client = TestClient(main.app)
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text("{}")

    captured = {}

    def fake_analyze_video(
        video_path,
        *,
        output_path=None,
        calibration_path=None,
        selected_action=None,
        analysis_template=None,
    ):
        captured["video_path"] = video_path
        captured["output_path"] = output_path
        captured["calibration_path"] = calibration_path
        captured["selected_action"] = selected_action
        captured["analysis_template"] = analysis_template
        assert video_path.exists()
        assert output_path is not None
        assert output_path.parent.exists()
        return {
            "status": "ok",
            "summary": "analyzed",
            "overall_score": 95.0,
        }

    monkeypatch.setattr(main, "run_video_analysis", fake_analyze_video)

    r = client.post(
        "/analyze_video",
        files={"video_file": ("demo.mp4", b"fake-video-bytes", "video/mp4")},
        data={
            "calibration_path": str(calibration_path),
            "selected_action": "pass",
            "analysis_template": "short_pass",
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["summary"] == "analyzed"
    assert data["overall_score"] == 95.0
    assert data["selected_action"] == "pass"
    assert data["analysis_routed_by"] == "user_selected"
    assert data["routed_analyzer"] == "pass"
    assert captured["video_path"].suffix == ".mp4"
    assert captured["calibration_path"] == calibration_path
    assert captured["selected_action"] == "pass"
    assert captured["analysis_template"] == "short_pass"

    stdout = capsys.readouterr().out
    assert "KICK_BACKEND_ENTER_ANALYZE_VIDEO_V2" in stdout
    assert "KICK_BACKEND_SELECTED_ACTION = pass" in stdout
    assert "KICK_BACKEND_ROUTED_ANALYZER = pass" in stdout
    assert "KICK_BACKEND_FINAL_RESPONSE_V2" in stdout


def test_analyze_video_endpoint_accepts_full_match(monkeypatch, tmp_path, capsys):
    client = TestClient(main.app)
    captured = {}

    def fake_analyze_video(
        video_path,
        *,
        output_path=None,
        calibration_path=None,
        selected_action=None,
        analysis_template=None,
    ):
        captured["selected_action"] = selected_action
        captured["analysis_template"] = analysis_template
        return {
            "status": "ok",
            "analysis_status": "success",
            "selected_action": selected_action,
            "analysis_routed_by": "user_selected",
            "routed_analyzer": "full_match_player_analyzer_v1",
            "action_display_name": "整场比赛",
            "recommended_template": "full_match_player",
            "match_analysis": {"capture": {"duration_s": 245.0}},
        }

    monkeypatch.setattr(main, "run_video_analysis", fake_analyze_video)

    r = client.post(
        "/analyze_video",
        files={"video_file": ("match.mp4", b"fake-video-bytes", "video/mp4")},
        data={
            "selected_action": "full_match",
            "analysis_template": "full_match_player",
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["selected_action"] == "full_match"
    assert data["analysis_routed_by"] == "user_selected"
    assert data["routed_analyzer"] == "full_match_player_analyzer_v1"
    assert data["action_display_name"] == "整场比赛"
    assert data["recommended_template"] == "full_match_player"
    assert data["match_analysis"]["capture"]["duration_s"] == 245.0
    assert captured["selected_action"] == "full_match"
    assert captured["analysis_template"] == "full_match_player"

    stdout = capsys.readouterr().out
    assert "KICK_BACKEND_SELECTED_ACTION = full_match" in stdout
    assert "KICK_BACKEND_ROUTED_ANALYZER = full_match_player_analyzer_v1" in stdout


def test_analyze_video_endpoint_accepts_full_match_alias(monkeypatch):
    client = TestClient(main.app)
    captured = {}

    def fake_analyze_video(*args, **kwargs):
        captured["selected_action"] = kwargs.get("selected_action")
        return {
            "status": "ok",
            "selected_action": kwargs.get("selected_action"),
            "analysis_routed_by": "user_selected",
            "routed_analyzer": "full_match_player_analyzer_v1",
            "action_display_name": "整场比赛",
            "recommended_template": "full_match_player",
            "match_analysis": {"capture": {"duration_s": 90.0}},
        }

    monkeypatch.setattr(main, "run_video_analysis", fake_analyze_video)

    r = client.post(
        "/analyze_video",
        files={"video_file": ("match.mp4", b"fake-video-bytes", "video/mp4")},
        data={"selected_action": "整场比赛"},
    )

    assert r.status_code == 200
    assert captured["selected_action"] == "full_match"
    assert r.json()["selected_action"] == "full_match"


def test_analyze_video_endpoint_returns_json_error(monkeypatch):
    client = TestClient(main.app)

    def fake_analyze_video(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "run_video_analysis", fake_analyze_video)

    r = client.post(
        "/analyze_video",
        files={"video_file": ("demo.mp4", b"fake-video-bytes", "video/mp4")},
        data={"selected_action": "pass"},
    )

    assert r.status_code == 500
    data = r.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "analysis_failed"
    assert "RuntimeError" in data["error"]["detail"]
    assert data["analysis_status"] == "failed"
    assert data["failure_reason"] == "unknown_error"
    assert data["long_video_localized"] is False
    assert data["candidate_window_count"] == 0
    assert data["selected_window_start_s"] is None
    assert data["selected_window_end_s"] is None
    assert data["selected_action"] == "pass"
    assert data["analysis_routed_by"] == "user_selected"
    assert data["routed_analyzer"] == "short_pass_analyzer_v1"


def test_analyze_video_endpoint_requires_selected_action():
    client = TestClient(main.app)

    r = client.post(
        "/analyze_video",
        files={"video_file": ("demo.mp4", b"fake-video-bytes", "video/mp4")},
    )

    assert r.status_code == 400
    data = r.json()
    assert data["status"] == "error"
    assert data["error_code"] == "missing_selected_action"
    assert data["error"]["code"] == "missing_selected_action"
    assert data["error"]["message"] == "请先选择本次分析动作类型"
    assert data["analysis_status"] == "failed"
    assert data["failure_reason"] == "unknown_error"
    assert data["long_video_localized"] is False
    assert data["candidate_window_count"] == 0
    assert data["analysis_routed_by"] == "request_validation"
    assert data["routed_analyzer"] == ""


def test_analyze_video_endpoint_returns_route_mismatch_payload(monkeypatch):
    client = TestClient(main.app)

    def fake_analyze_video(*args, **kwargs):
        return {
            "status": "failed",
            "analysis_status": "failed",
            "failure_reason": "route_mismatch",
            "failure_message": "本次结果存在异常，请重新分析。",
            "selected_action": "pass",
            "analysis_routed_by": "user_selected",
            "routed_analyzer": "shot_instep",
            "system_action_suggestion": "shot",
            "integrity_state": "anomaly",
            "route_mismatch_message": "你当前选择的是“传球”，但系统自动识别更像“射门”。",
            "warnings": ["route_mismatch"],
            "summary": "本次结果存在异常，请重新分析。",
        }

    monkeypatch.setattr(main, "run_video_analysis", fake_analyze_video)

    r = client.post(
        "/analyze_video",
        files={"video_file": ("demo.mp4", b"fake-video-bytes", "video/mp4")},
        data={"selected_action": "pass"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["analysis_status"] == "failed"
    assert data["failure_reason"] == "route_mismatch"
    assert data["selected_action"] == "pass"
    assert data["analysis_routed_by"] == "user_selected"
    assert data["routed_analyzer"] == "shot_instep"
    assert data["integrity_state"] == "anomaly"
    assert data["route_mismatch_message"]
    assert data["warnings"] == ["route_mismatch"]


def test_analysis_timeout_does_not_fire_for_valid_long_running_result():
    payload = {
        "status": "ok",
        "score": {"overall": 87.0},
        "overall_score": 87.0,
        "warnings": [],
    }

    run_data = {
        "frame_count": 300,
        "sampled_frame_count": 30,
        "warnings": [],
        "fast_mode_enabled": False,
    }

    probe = {
        "duration_s": 12.9,
        "frame_count": 300,
        "warnings": [],
    }

    failure_reason, analysis_status, integrity_state, route_mismatch_message = shot_analysis._video_detect_failure_reason(
        payload,
        run_data=run_data,
        probe=probe,
        processing_time_s=21.0,
        selected_action="pass",
        routed_analyzer="pass",
        system_action_suggestion="pass",
        long_video_localized=False,
    )

    assert failure_reason is None
    assert analysis_status == "success"
    assert integrity_state == "normal"
    assert route_mismatch_message is None


def test_analysis_result_is_not_failed_when_score_and_summary_exist_but_sampled_frames_are_zero():
    payload = {
        "status": "provisional",
        "score": {"overall": 46.4},
        "overall_score": 46.4,
        "summary": "传球 动作得分 46/100，当前主要问题是视频证据不足，建议先把这个环节稳定下来。",
        "warnings": [],
    }

    run_data = {
        "frame_count": 327,
        "sampled_frame_count": 0,
        "warnings": [],
        "fast_mode_enabled": False,
    }

    probe = {
        "duration_s": 10.902,
        "frame_count": 327,
        "warnings": [],
    }

    failure_reason, analysis_status, integrity_state, route_mismatch_message = shot_analysis._video_detect_failure_reason(
        payload,
        run_data=run_data,
        probe=probe,
        processing_time_s=26.355,
        selected_action="pass",
        routed_analyzer="short_pass_analyzer_v1",
        system_action_suggestion="shot",
        long_video_localized=True,
    )

    assert failure_reason is None
    assert analysis_status == "partial"
    assert integrity_state == "route_mismatch"
    assert route_mismatch_message == "你当前选择的是“传球”，但系统自动识别更像“射门”，已按当前选择继续分析。"


def test_analyze_video_endpoint_requires_file():
    client = TestClient(main.app)

    r = client.post("/analyze_video")
    assert r.status_code == 400
    data = r.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "missing_video_file"
    assert data["analysis_status"] == "failed"
    assert data["failure_reason"] == "unknown_error"
    assert data["long_video_localized"] is False
    assert data["candidate_window_count"] == 0
    assert data["analysis_routed_by"] == "request_validation"
