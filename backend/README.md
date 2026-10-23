# Kick · Analysis Backend

**English** · [简体中文](README.zh-CN.md)

Video analysis, training plans, and football discovery APIs for the Kick iOS app. The FastAPI entry point is `main.py`; movement analysis is handled by modules in `analysis/`.

[Project Home](../README.md) · [iOS Integration](../ios/KickAI/README.md)

## Local Setup

Requires Python 3.10 or later. Dependency versions are not pinned; verify installation and model compatibility in your target environment.

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Keep `backend/` as the working directory so relative data and configuration paths resolve correctly.

- Health endpoint: `GET http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

Analysis modules preload in the background. Inspect `analyzer_availability.video_analysis` in the health response: `pending` means loading has not finished, `available` means the module was imported, and `degraded` means loading failed. A successful import does not validate real-video analysis; also inspect `startup_warnings` and actual request results.

## Configuration

The application reads process environment variables and does not automatically load `.env`. To configure map lookup, load your local file in the current terminal before starting the service:

```bash
cp .env.example .env
# Edit .env first and add your own map credential.
set -a
source .env
set +a
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

| Variable | Purpose | Default |
| --- | --- | --- |
| `KICK_AMAP_KEY` | Amap service credential | Unset |
| `KICK_ENABLE_OSM_FALLBACK` | Try OpenStreetMap when a map provider is unavailable | Enabled |
| `KICK_DB_PATH` | Training-plan SQLite database path | `./data/plans.db` |
| `KICK_DISCOVERY_DB_PATH` | Discovery data file path | `./data/discovery.json` |
| `KICK_BACKEND_VERSION` | Service version reported by the health endpoint | `local-dev` |

Map lookup requires network access. Results depend on provider availability and regional coverage. Keep `.env` local.

## Video Analysis API

`POST /analyze_video` accepts `multipart/form-data`:

| Field | Description |
| --- | --- |
| `video_file` | Video file to upload |
| `selected_action` | Explicit movement selection |
| `analysis_template` | Optional template hint; the action route determines the actual template |

Current routes:

| Movement | `selected_action` | Template |
| --- | --- | --- |
| Passing | `pass` | `short_pass` |
| Shooting | `shot` | `shot_instep` |
| Receiving and control | `receive_control` | `receive_control` |
| Pass-receive sequence | `pass_receive_sequence` | `pass_receive_sequence` |
| Single-player long video | `full_match` | `full_match_player` |

Example: upload the included short clip from `backend/`. This demonstrates the request format; the sample is not guaranteed to produce a valid score.

```bash
curl --fail-with-body http://127.0.0.1:8000/analyze_video \
  -F "video_file=@tests/samples/sample_short.mp4" \
  -F "selected_action=pass" \
  -F "analysis_template=short_pass"
```

Clients should inspect `analysis_status`, `failure_reason`, `warnings`, and routing information. HTTP 200 can still contain a partial result or failed analysis and must not be treated as a valid score on its own.

## Additional APIs

| Endpoint | Purpose |
| --- | --- |
| `POST /generate_plan` | Generate and save a training plan |
| `GET /plan/{plan_id}` | Retrieve a training plan |
| `DELETE /plan/{plan_id}` | Delete a training plan |
| `/discovery/community/…` | Community posts, likes, and comments |
| `GET /discovery/venues/search` | Venue search |
| `/discovery/coaches…` | Coach listings, bookings, and conversations |

Use the running service's `/docs` for parameters and request schemas. API availability does not imply that payments, real-world coaching fulfillment, or production deployment are complete.

## Validation & Code Guide

```bash
python -m pytest
```

- `analysis/analyzer_router.py`: movement and template routing.
- `analysis/shot_analysis.py`: video analysis entry point and result assembly.
- `analysis/football_scoring.py`: football movement scoring.
- `analysis/long_video_locator.py`: candidate action windows in long videos.
- `vision/`: pose detection and keypoint processing.
- `tests/`: API, movement, scoring, and consistency tests.

## Research & Earlier Implementations

The repository also retains experimental tools such as `pipeline.py`, `coach.py`, dataset indexing, and `NeuroMiniGame.js`. These have separate data and dependency requirements and are outside the API setup described above.

[Biomechanics References (Chinese)](docs/biomechanics_reference.md) · [Dataset Schema](datasets/schema.md)

`scripts/run_kick_backend.sh` contains absolute paths from the original development machine. Use the commands in this guide for other environments.
