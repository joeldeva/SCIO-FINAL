# Sciobraille Backend Deployment

The Android app sends camera frames to the scanner backend. For Play release,
deploy `backend/scanner_api.py` behind HTTPS and set the app's backend URL at
build time.

## Runtime

Use a Python environment with the packages in `backend/requirements.txt`.

```powershell
cd backend
python scanner_api.py
```

Required files:

- `scanner_api.py`
- `inference.py`
- `model/best.pt`
- `model/model_info.md`

## Health Check

The service must expose:

- `GET /api/health`
- `POST /api/scan-frame`
- `WS /ws/scan`

Example expected health payload:

```json
{
  "ok": true,
  "status": "ok",
  "classes": 26
}
```

## Android Build URL

For release, pass a real HTTPS backend URL:

```powershell
cd android
powershell.exe -ExecutionPolicy Bypass -File .\build_cached_gradle.ps1 :app:bundleRelease -PSCIOBRAILLE_BACKEND_URL=https://api.your-domain.example
```

Do not use plain HTTP in release builds. The release manifest disables cleartext
traffic.

The Android app uses `/ws/scan` for live streaming. Keep `/api/scan-frame` for
tests, diagnostics, and upload-style backend checks.
