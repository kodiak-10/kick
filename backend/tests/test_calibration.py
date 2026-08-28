from analysis import calibration


def test_open_camera_with_attempts_promotes_selected_source(monkeypatch):
    probe_record = {
        "kind": "camera_index",
        "value": 3,
        "backend": "CAP_AVFOUNDATION",
        "source_label": "camera_index:3 (CAP_AVFOUNDATION)",
        "probe_opened": True,
        "probe_readable": True,
        "probe_status": "success",
        "probe_reads": 1,
        "probe_frame_mean": 42.0,
        "final_opened": False,
        "final_read_succeeded": False,
        "final_status": "pending",
        "final_reads": 0,
        "final_frame_mean": None,
        "selected": False,
    }

    def fake_probe(*, kind, value, backend_name=None, backend_value=None, probe_reads=12):
        record = dict(probe_record)
        record["kind"] = kind
        record["value"] = value
        record["backend"] = backend_name or "default"
        record["source_label"] = f"{kind}:{value} ({record['backend']})"
        return record

    def fake_final(source_record, final_reads=3):
        record = dict(source_record)
        record["final_opened"] = True
        record["final_read_succeeded"] = True
        record["final_status"] = "success"
        record["final_reads"] = 1
        record["final_frame_mean"] = 41.0
        return object(), record

    monkeypatch.setattr(calibration, "_probe_camera_source", fake_probe)
    monkeypatch.setattr(calibration, "_final_open_camera_source", fake_final)

    result = calibration._open_camera_with_attempts(camera_index=3)

    assert result["ok"] is True
    assert result["selected_source"] is not None
    assert result["opened_source"] is not None
    assert result["selected_source"]["probe_readable"] is True
    assert result["opened_source"]["final_opened"] is True
    assert result["opened_source"]["final_read_succeeded"] is True


def test_calibrate_live_keeps_selected_source_on_open_failure(monkeypatch, tmp_path):
    attempts = [
        {
            "kind": "camera_index",
            "value": 3,
            "backend": "CAP_AVFOUNDATION",
            "source_label": "camera_index:3 (CAP_AVFOUNDATION)",
            "probe_opened": True,
            "probe_readable": True,
            "probe_status": "success",
            "probe_reads": 1,
            "probe_frame_mean": 42.0,
            "final_opened": False,
            "final_read_succeeded": False,
            "final_status": "open_failed",
            "final_reads": 0,
            "final_frame_mean": None,
            "selected": True,
        }
    ]

    def fake_open(*args, **kwargs):
        return {
            "ok": False,
            "cap": None,
            "selected_source": attempts[0],
            "opened_source": None,
            "attempts": attempts,
        }

    monkeypatch.setattr(calibration, "_open_camera_with_attempts", fake_open)

    result = calibration.calibrate_live(
        camera_index=3,
        user_height_m=1.70,
        out_path=tmp_path / "user_profile.json",
    )

    assert result["ok"] is False
    assert result["error_code"] == "camera_open_failed"
    assert result["selected_source"] is not None
    assert result["selected_source"]["probe_readable"] is True
    assert result["attempts"] == attempts
