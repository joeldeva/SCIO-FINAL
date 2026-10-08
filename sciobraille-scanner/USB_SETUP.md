# Sciobraille USB Scanner Setup

The USB APK calls `http://127.0.0.1:8000` on the Android phone. ADB reverse
forwards that address through the USB cable to the FastAPI backend running on
the laptop at `http://127.0.0.1:8088`.

## One-Time Phone Setup

1. Enable Developer options on the Android phone.
2. Enable USB debugging.
3. Connect a USB data cable and choose File transfer if Android asks.
4. Unlock the phone and accept the USB debugging authorization prompt.

## Start Sciobraille

1. Keep `backend/start_backend.bat` running on the laptop.
2. Double-click `CONNECT_PHONE_USB.bat`.
3. The script installs or updates `releases/Sciobraille-v1.1.9-USB.apk`.
4. The script creates `tcp:8000 -> tcp:8088` and verifies the tunnel.
5. Open Sciobraille and scan normally. Wi-Fi and mobile data are not needed.

Run `CONNECT_PHONE_USB.bat` again after reconnecting the cable, restarting the
phone, or restarting ADB. If APK installation reports an incompatible
signature, uninstall the previous Sciobraille build first; this removes its
local history and learning progress.

To verify the tunnel from the phone, open:

`http://127.0.0.1:8000/api/health`
