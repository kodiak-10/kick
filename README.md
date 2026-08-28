# Kick

Kick is a football video-analysis product with an iOS client and a Python/FastAPI analysis backend. The current product supports controlled analysis flows for passing, shooting, and pass-receive sequences, along with discovery, venues, coach entry points, and playback feedback.

## Repository layout

```text
Kick/
├── ios/KickAI/       # Primary SwiftUI iOS app and Xcode project
├── ios/AICoach/      # Earlier iOS implementation retained for reference
└── backend/          # FastAPI service, analysis pipeline, tests, docs, and models
```

`ios/KickAI` is the active app project. The `ios/AICoach` directory is retained because it contains earlier work that may still be useful for migration or comparison.

## Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

For a physical iPhone, configure the iOS app to use your Mac's LAN address, for example `http://192.168.x.x:8000`. `127.0.0.1` only reaches the device itself.

## Run the iOS app

1. Open `ios/KickAI/Kick.xcodeproj` in Xcode.
2. Select the `KickAI` scheme and a simulator or device.
3. Configure the backend base URL for the selected device.

## Environment variables

Copy `backend/.env.example` to `backend/.env` before starting the backend. Real map keys, API credentials, user videos, reports, logs, caches, and Xcode build products are intentionally excluded from Git.

## Validation

```bash
cd backend
pytest
```

## Security

Do not commit map keys, production endpoints with embedded credentials, user-uploaded videos, device logs, or generated reports. If a key was ever committed, rotate it in the provider console before making the repository public.
