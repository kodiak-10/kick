import json
import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from analysis.analyzer_router import resolve_analysis_route

_MPL_CACHE = Path(__file__).resolve().parent / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

BACKEND_SERVICE_NAME = "analysis_backend"
BACKEND_VERSION = os.getenv("KICK_BACKEND_VERSION", "local-dev")
BACKEND_HOST = os.getenv("KICK_BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("KICK_BACKEND_PORT", "8000"))
BACKEND_RELOAD = os.getenv("KICK_BACKEND_RELOAD", "0").strip().lower() in {"1", "true", "yes", "on"}
BACKEND_LOG_LEVEL = os.getenv("KICK_BACKEND_LOG_LEVEL", "info")
DB_PATH = os.getenv("KICK_DB_PATH", "./data/plans.db")
DEFAULT_CALIBRATION_PATH = Path("calibration/user_profile.json")

_STARTUP_WARNINGS: list[str] = []
_ANALYSIS_IMPORT_LOCK = threading.Lock()
_ANALYSIS_RUNNER = None
_ANALYSIS_IMPORT_ERROR: Exception | None = None
_ANALYSIS_IMPORT_STATUS = "pending"


def _log_backend_event(event: str, **fields) -> None:
    payload = json.dumps(fields, ensure_ascii=False, default=str, sort_keys=True)
    print(f"[{event}] {payload}", flush=True)


def _analysis_runner_unavailable(*args, **kwargs):
    raise RuntimeError(
        f"analysis backend unavailable: {type(_ANALYSIS_IMPORT_ERROR).__name__}: {_ANALYSIS_IMPORT_ERROR}"
    )


def _ensure_video_analysis_runner():
    global _ANALYSIS_RUNNER, _ANALYSIS_IMPORT_ERROR, _ANALYSIS_IMPORT_STATUS
    if _ANALYSIS_RUNNER is not None:
        return _ANALYSIS_RUNNER
    with _ANALYSIS_IMPORT_LOCK:
        if _ANALYSIS_RUNNER is not None:
            return _ANALYSIS_RUNNER
        try:
            from analysis.shot_analysis import analyze_video as _analyze_video
        except Exception as analysis_import_error:  # pragma: no cover - import guard for service startup
            _ANALYSIS_IMPORT_ERROR = analysis_import_error
            _ANALYSIS_IMPORT_STATUS = "degraded"
            _STARTUP_WARNINGS.append(
                f"analysis.shot_analysis import failed: {type(analysis_import_error).__name__}: {analysis_import_error}"
            )
            _log_backend_event(
                "KICK_BACKEND_IMPORT_ERROR",
                module="analysis.shot_analysis",
                exception_type=type(analysis_import_error).__name__,
                exception_message=str(analysis_import_error),
            )
            _ANALYSIS_RUNNER = _analysis_runner_unavailable
        else:
            _ANALYSIS_RUNNER = _analyze_video
            _ANALYSIS_IMPORT_STATUS = "available"
        return _ANALYSIS_RUNNER


def run_video_analysis(*args, **kwargs):
    return _ensure_video_analysis_runner()(*args, **kwargs)

try:
    from models import Plan, init_db
except Exception as model_import_error:  # pragma: no cover - import guard for service startup
    Plan = None  # type: ignore[assignment]
    init_db = None  # type: ignore[assignment]
    SessionLocal = None
    _STARTUP_WARNINGS.append(
        f"models import failed: {type(model_import_error).__name__}: {model_import_error}"
    )
    _log_backend_event(
        "KICK_BACKEND_IMPORT_ERROR",
        module="models",
        exception_type=type(model_import_error).__name__,
        exception_message=str(model_import_error),
    )
else:
    try:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        SessionLocal = init_db(DB_PATH)
    except Exception as model_init_error:  # pragma: no cover - import guard for service startup
        SessionLocal = None
        _STARTUP_WARNINGS.append(
            f"models/init_db failed: {type(model_init_error).__name__}: {model_init_error}"
        )
        _log_backend_event(
            "KICK_BACKEND_IMPORT_ERROR",
            module="models",
            exception_type=type(model_init_error).__name__,
            exception_message=str(model_init_error),
        )

app = FastAPI(title="KickAI Analysis Backend")
print(
    "KICK_BACKEND_BOOTSTRAP_V3 supported_selected_actions=pass,shot,pass_receive_sequence,receive_control,full_match",
    flush=True,
)

try:
    from discovery_backend import router as discovery_router
except Exception as discovery_import_error:  # pragma: no cover - startup guard
    discovery_router = None
    _STARTUP_WARNINGS.append(
        f"discovery_backend import failed: {type(discovery_import_error).__name__}: {discovery_import_error}"
    )
    _log_backend_event(
        "KICK_BACKEND_IMPORT_ERROR",
        module="discovery_backend",
        exception_type=type(discovery_import_error).__name__,
        exception_message=str(discovery_import_error),
    )
else:
    app.include_router(discovery_router)
    print("KICK_BACKEND_DISCOVERY_ROUTER_READY", flush=True)


class GenerateRequest(BaseModel):
    user_profile: dict
    explain_output: dict
    goals: dict


class PlanResponse(BaseModel):
    id: int
    plan: dict


def _analysis_availability() -> str:
    if _ANALYSIS_IMPORT_ERROR is not None:
        return "degraded"
    if _ANALYSIS_RUNNER is None:
        return "pending"
    return "available"


def _plan_service_available() -> bool:
    return SessionLocal is not None and Plan is not None


def _startup_status() -> str:
    if _ANALYSIS_IMPORT_ERROR is not None or not _plan_service_available():
        return "degraded"
    return "ok"


def _request_host_port(request: Request) -> tuple[str, int]:
    server = request.scope.get("server")
    if isinstance(server, (tuple, list)) and len(server) == 2:
        host = str(server[0] or BACKEND_HOST)
        try:
            port = int(server[1])
        except (TypeError, ValueError):
            port = BACKEND_PORT
        return host, port
    return BACKEND_HOST, BACKEND_PORT


def _error_response(status_code: int, code: str, message: str, *, detail: str | None = None):
    payload = {
        "status": "error",
        "error_code": code,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if detail:
        payload["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)


@app.on_event("startup")
def _startup_event() -> None:
    _log_backend_event(
        "KICK_BACKEND_START",
        service=BACKEND_SERVICE_NAME,
        version=BACKEND_VERSION,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        host_port=f"{BACKEND_HOST}:{BACKEND_PORT}",
        analysis_import_status=_analysis_availability(),
        analyzer_availability={
            "video_analysis": _analysis_availability(),
            "plan_db": "available" if _plan_service_available() else "degraded",
        },
        startup_warnings=list(_STARTUP_WARNINGS),
    )
    warmup_thread = threading.Thread(target=_warmup_video_analysis_import, name="kick-backend-warmup", daemon=True)
    warmup_thread.start()


def _warmup_video_analysis_import() -> None:
    try:
        _ensure_video_analysis_runner()
    except Exception:
        # The import helper already logs the failure; keep startup resilient.
        pass


@app.middleware("http")
async def _request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    host, port = _request_host_port(request)
    try:
        response = await call_next(request)
    except Exception as exc:  # pragma: no cover - defensive logging
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        _log_backend_event(
            "KICK_BACKEND_REQUEST",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            host=host,
            port=port,
            status_code=500,
            elapsed_ms=elapsed_ms,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
        )
        if request.url.path == "/analyze_video":
            _log_backend_event(
                "KICK_BACKEND_ANALYSIS_FAILURE",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                host=host,
                port=port,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    _log_backend_event(
        "KICK_BACKEND_REQUEST",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        host=host,
        port=port,
        status_code=getattr(response, "status_code", None),
        elapsed_ms=elapsed_ms,
    )
    if request.url.path == "/health":
        _log_backend_event(
            "KICK_BACKEND_HEALTH",
            request_id=request_id,
            status=_startup_status(),
            service=BACKEND_SERVICE_NAME,
            version=BACKEND_VERSION,
            host=host,
            port=port,
            analyzer_availability={
                "video_analysis": _analysis_availability(),
                "plan_db": "available" if _plan_service_available() else "degraded",
            },
            startup_warnings=list(_STARTUP_WARNINGS),
        )
    return response


def _analysis_error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    selected_action: str = "",
    analysis_routed_by: str = "request_validation",
    routed_analyzer: str = "",
    system_action_suggestion: str = "",
    failure_reason: str = "unknown_error",
    warnings: list[str] | None = None,
    detail: str | None = None,
):
    response = _error_response(status_code, code, message, detail=detail)
    payload = json.loads(response.body.decode("utf-8"))
    payload.update(
        {
            "analysis_status": "failed",
            "failure_reason": failure_reason,
            "failure_message": message,
            "selected_action": selected_action,
            "analysis_routed_by": analysis_routed_by,
            "routed_analyzer": routed_analyzer,
            "system_action_suggestion": system_action_suggestion,
            "fast_mode_enabled": False,
            "long_video_localized": False,
            "candidate_window_count": 0,
            "selected_window_index": None,
            "selected_window_start_s": None,
            "selected_window_end_s": None,
            "selected_window_duration_s": None,
            "candidate_windows": [],
            "selected_window": None,
            "sampled_frame_count": 0,
            "video_duration_s": 0.0,
            "frame_count": 0,
            "processing_time_s": 0.0,
            "debug_context": {
                "selected_action": selected_action,
                "system_action_suggestion": system_action_suggestion,
                "analysis_routed_by": analysis_routed_by,
                "routed_analyzer": routed_analyzer,
                "failure_reason": failure_reason,
                "analysis_status": "failed",
                "long_video_localized": False,
                "candidate_window_count": 0,
                "selected_window_index": None,
                "selected_window_start_s": None,
                "selected_window_end_s": None,
                "selected_window_duration_s": None,
                "warnings": warnings or [code],
            },
        }
    )
    if warnings is not None:
        payload["warnings"] = warnings
    return JSONResponse(status_code=status_code, content=payload)


def _generate_plan(user_profile, explain_output, goals):
    # Simple 8-week template
    weeks = []
    for w in range(1, 9):
        weeks.append({
            "week": w,
            "focus": goals.get("focus", "strength"),
            "sessions": [
                {"day": "Mon", "exercises": ["squat", "pushup"], "sets": 3, "reps": 10},
                {"day": "Wed", "exercises": ["lunge", "row"], "sets": 3, "reps": 10},
                {"day": "Fri", "exercises": ["hinge", "plank"], "sets": 3, "reps": 10},
            ],
            "progression": "increase reps by 1 each week",
        })
    return {"weeks": weeks, "notes": "Auto-generated plan"}


@app.post("/generate_plan", response_model=PlanResponse)
def generate_plan(req: GenerateRequest):
    if not _plan_service_available():
        raise HTTPException(status_code=503, detail="plan service unavailable")

    plan = _generate_plan(req.user_profile, req.explain_output, req.goals)
    db = SessionLocal()
    p = Plan(
        user_profile=json.dumps(req.user_profile),
        explain_output=json.dumps(req.explain_output),
        goals=json.dumps(req.goals),
        plan=json.dumps(plan),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PlanResponse(id=p.id, plan=plan)


@app.get("/health")
def health_check(request: Request):
    host, port = _request_host_port(request)
    return {
        "status": _startup_status(),
        "service": BACKEND_SERVICE_NAME,
        "host": host,
        "port": port,
        "version": BACKEND_VERSION,
        "analyzer_availability": {
            "video_analysis": _analysis_availability(),
            "plan_db": "available" if _plan_service_available() else "degraded",
            "discovery": "available" if discovery_router is not None else "degraded",
        },
        "startup_warnings": list(_STARTUP_WARNINGS),
    }


@app.post("/analyze_video")
def analyze_video_endpoint(
    request: Request,
    video_file: UploadFile | None = File(default=None),
    calibration_path: str | None = Form(default=None),
    selected_action: str | None = Form(default=None),
    selectedAction: str | None = Form(default=None),
    action: str | None = Form(default=None),
    analysis_template: str | None = Form(default=None),
):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    host, port = _request_host_port(request)
    print("KICK_BACKEND_ENTER_ANALYZE_VIDEO_V2", flush=True)
    raw_selected_action_value = str(selected_action or selectedAction or action or "").strip()
    selected_action_value = raw_selected_action_value.lower()
    selected_route = resolve_analysis_route(
        selected_action_value,
        analysis_template=analysis_template,
        analysis_routed_by="user_selected" if selected_action_value else "request_validation",
    )
    canonical_selected_action = selected_route.selected_action
    print(f"KICK_BACKEND_SELECTED_ACTION = {selected_action_value}", flush=True)
    print(f"KICK_BACKEND_SELECTED_ACTION_RAW = {selected_action}", flush=True)
    _log_backend_event(
        "KICK_BACKEND_ANALYSIS_ROUTE",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        host=host,
        port=port,
            selected_action=canonical_selected_action or selected_action_value,
            analysis_routed_by="user_selected" if selected_action_value else "auto_detected",
            routed_analyzer=selected_route.routed_analyzer or selected_action_value or "",
            system_action_suggestion=str(analysis_template or ""),
    )
    if video_file is None:
        response = _analysis_error_response(
            400,
            "missing_video_file",
            "请通过 multipart/form-data 上传视频文件。",
            selected_action=canonical_selected_action or selected_action_value,
            analysis_routed_by="request_validation",
            routed_analyzer="",
            system_action_suggestion="",
            failure_reason="unknown_error",
        )
        _log_backend_event(
            "KICK_BACKEND_ANALYSIS_FAILURE",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            host=host,
            port=port,
            selected_action=canonical_selected_action or selected_action_value,
            routed_analyzer="",
            failure_reason="unknown_error",
            exception_type="ValidationError",
            exception_message="missing_video_file",
        )
        print("KICK_BACKEND_ROUTED_ANALYZER = NONE", flush=True)
        print("KICK_BACKEND_FINAL_RESPONSE_V2", flush=True)
        return response

    if not selected_action_value:
        response = _analysis_error_response(
            400,
            "missing_selected_action",
            "请先选择本次分析动作类型",
            selected_action="",
            analysis_routed_by="request_validation",
            routed_analyzer="",
            system_action_suggestion="",
            failure_reason="unknown_error",
        )
        _log_backend_event(
            "KICK_BACKEND_ANALYSIS_FAILURE",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            host=host,
            port=port,
            selected_action="",
            routed_analyzer="",
            failure_reason="unknown_error",
            exception_type="ValidationError",
            exception_message="missing_selected_action",
        )
        print("KICK_BACKEND_ROUTED_ANALYZER = NONE", flush=True)
        print("KICK_BACKEND_FINAL_RESPONSE_V2", flush=True)
        return response
    if selected_route.failure_reason == "unsupported_action" or not selected_route.routed_analyzer:
        response = _analysis_error_response(
            400,
            "invalid_selected_action",
            "selected_action 仅支持 pass、shot、pass_receive_sequence、receive_control、full_match（也兼容 full_match_player、整场比赛、全场）。",
            selected_action=canonical_selected_action or selected_action_value,
            analysis_routed_by="request_validation",
            routed_analyzer="",
            system_action_suggestion="",
            failure_reason="unsupported_action",
        )
        _log_backend_event(
            "KICK_BACKEND_ANALYSIS_FAILURE",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            host=host,
            port=port,
            selected_action=canonical_selected_action or selected_action_value,
            routed_analyzer="",
            failure_reason="unsupported_action",
            exception_type="ValidationError",
            exception_message="invalid_selected_action",
        )
        print("KICK_BACKEND_ROUTED_ANALYZER = NONE", flush=True)
        print("KICK_BACKEND_FINAL_RESPONSE_V2", flush=True)
        return response

    original_name = Path(video_file.filename or "upload.mp4").name
    if not Path(original_name).suffix:
        original_name = f"{original_name}.mp4"

    calibration_candidate = calibration_path or str(DEFAULT_CALIBRATION_PATH)
    calibration_file = Path(calibration_candidate)
    if not calibration_file.exists():
        calibration_file = None

    try:
        with tempfile.TemporaryDirectory(prefix="kick_ai_analysis_") as temp_dir:
            temp_dir_path = Path(temp_dir)
            temp_video_path = temp_dir_path / original_name
            output_path = temp_dir_path / f"{temp_video_path.stem}_analysis.json"

            with temp_video_path.open("wb") as destination:
                shutil.copyfileobj(video_file.file, destination)

            try:
                payload = run_video_analysis(
                    temp_video_path,
                    output_path=output_path,
                    calibration_path=calibration_file,
                    selected_action=canonical_selected_action or selected_action_value,
                    analysis_template=analysis_template,
                )
            except Exception as exc:
                response = _analysis_error_response(
                    500,
                    "analysis_failed",
                    "视频分析失败，请稍后重试。",
                    selected_action=canonical_selected_action or selected_action_value,
                    analysis_routed_by="user_selected" if selected_action_value else "auto_detected",
                    routed_analyzer=selected_route.routed_analyzer or canonical_selected_action or selected_action_value or "",
                    system_action_suggestion="",
                    failure_reason="unknown_error",
                    warnings=[type(exc).__name__],
                    detail=f"{type(exc).__name__}: {exc}",
                )
                _log_backend_event(
                    "KICK_BACKEND_ANALYSIS_FAILURE",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    host=host,
                    port=port,
                    selected_action=canonical_selected_action or selected_action_value,
                    routed_analyzer=selected_route.routed_analyzer or canonical_selected_action or selected_action_value or "",
                    failure_reason="unknown_error",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                )
                print("KICK_BACKEND_ROUTED_ANALYZER = ERROR", flush=True)
                print("KICK_BACKEND_SYSTEM_ACTION_SUGGESTION = ", flush=True)
                print("KICK_BACKEND_ANALYSIS_STATUS = failed", flush=True)
                print("KICK_BACKEND_FAILURE_REASON = unknown_error", flush=True)
                print(f"KICK_BACKEND_WARNINGS = {json.dumps([type(exc).__name__], ensure_ascii=False)}", flush=True)
                print("KICK_BACKEND_FINAL_RESPONSE_V2", flush=True)
                return response

            payload = dict(payload)
            payload_selected_action = str(payload.get("selected_action") or selected_action_value or "").strip().lower()
            payload_analysis_routed_by = str(
                payload.get("analysis_routed_by")
                or ("user_selected" if payload_selected_action else "auto_detected")
            ).strip()
            routed_analyzer = str(
                payload.get("routed_analyzer")
                or payload.get("analyzer_used")
                or payload_selected_action
                or ""
            ).strip()

            if not payload.get("selected_action"):
                payload["selected_action"] = payload_selected_action
            if not payload.get("analysis_routed_by"):
                payload["analysis_routed_by"] = payload_analysis_routed_by
            if not payload.get("routed_analyzer"):
                payload["routed_analyzer"] = routed_analyzer
            if not payload.get("system_action_suggestion"):
                payload["system_action_suggestion"] = str(payload.get("suggested_action") or "")
            if not payload.get("analysis_status"):
                payload["analysis_status"] = "failed" if payload.get("failure_reason") else ("partial" if payload.get("fast_mode_enabled") else "success")
            if "failure_reason" not in payload:
                payload["failure_reason"] = None
            if "failure_message" not in payload:
                payload["failure_message"] = None
            if not payload.get("debug_context"):
                payload["debug_context"] = {
                    "selected_action": payload.get("selected_action", ""),
                    "system_action_suggestion": payload.get("system_action_suggestion", ""),
                    "analysis_routed_by": payload.get("analysis_routed_by", ""),
                    "routed_analyzer": payload.get("routed_analyzer", ""),
                    "video_duration": payload.get("video_duration_s", payload.get("duration_s", 0.0)),
                    "frame_count": payload.get("frame_count", 0),
                    "sampled_frame_count": payload.get("sampled_frame_count", 0),
                    "fast_mode_enabled": payload.get("fast_mode_enabled", False),
                    "failure_reason": payload.get("failure_reason"),
                    "warnings": payload.get("warnings", []),
                }

            print(f"KICK_BACKEND_ROUTED_ANALYZER = {routed_analyzer}", flush=True)
            print(f"KICK_BACKEND_SYSTEM_ACTION_SUGGESTION = {payload.get('system_action_suggestion', '')}", flush=True)
            print(f"KICK_BACKEND_ANALYSIS_STATUS = {payload.get('analysis_status', '')}", flush=True)
            print(f"KICK_BACKEND_FAILURE_REASON = {payload.get('failure_reason', '')}", flush=True)
            print(f"KICK_BACKEND_WARNINGS = {json.dumps(payload.get('warnings', []), ensure_ascii=False)}", flush=True)
            _log_backend_event(
                "KICK_BACKEND_ANALYSIS_RESULT",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                host=host,
                port=port,
                selected_action=payload.get("selected_action", selected_action_value),
                analysis_routed_by=payload.get("analysis_routed_by", ""),
                routed_analyzer=payload.get("routed_analyzer", ""),
                analysis_status=payload.get("analysis_status", ""),
                failure_reason=payload.get("failure_reason", ""),
                warnings=payload.get("warnings", []),
            )
            print("KICK_BACKEND_FINAL_RESPONSE_V2", flush=True)
            return payload
    finally:
        try:
            video_file.file.close()
        except Exception:
            pass


@app.get("/plan/{plan_id}")
def get_plan(plan_id: int):
    if not _plan_service_available():
        raise HTTPException(status_code=503, detail="plan service unavailable")
    db = SessionLocal()
    p = db.query(Plan).filter(Plan.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"id": p.id, "plan": json.loads(p.plan)}


@app.delete("/plan/{plan_id}")
def delete_plan(plan_id: int):
    if not _plan_service_available():
        raise HTTPException(status_code=503, detail="plan service unavailable")
    db = SessionLocal()
    p = db.query(Plan).filter(Plan.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="plan not found")
    db.delete(p)
    db.commit()
    return {"status": "deleted", "id": plan_id}


# Example:
# curl -X POST http://127.0.0.1:8000/generate_plan \\
#   -H 'Content-Type: application/json' \\
#   -d '{"user_profile":{"age":30},"explain_output":{"fault_label":"knee_valgus"},"goals":{"focus":"strength"}}'
#
# Response:
# {"id":1,"plan":{"weeks":[{"week":1,"focus":"strength",...}],"notes":"Auto-generated plan"}}
#
# Run locally:
#   python main.py
# or:
#   uvicorn main:app --host 0.0.0.0 --port 8000


if __name__ == "__main__":
    import uvicorn

    uvicorn_target = "main:app" if BACKEND_RELOAD else app
    uvicorn.run(
        uvicorn_target,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=BACKEND_RELOAD,
        log_level=BACKEND_LOG_LEVEL,
    )
#
# Analyze video:
# curl -X POST http://127.0.0.1:8000/analyze_video \\
#   -F "video_file=@/path/to/video.mp4" \\
#   -F "calibration_path=calibration/user_profile.json"
