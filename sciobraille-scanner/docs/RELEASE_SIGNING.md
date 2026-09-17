# Sciobraille Release Signing

The project supports Play upload signing without storing passwords or keystores
in source control.

## Current Local Upload Key

A local upload keystore has been generated for this machine at:

```text
C:/Users/devaj/.sciobraille/keystores/sciobraille-upload.jks
```

The corresponding signing values are stored in:

```text
android/local.properties
```

Do not upload `local.properties` or the `.jks` file to GitHub. Back up the
keystore and password values in a secure password manager before creating the
Play Console app. If this file is lost after Play upload signing is configured,
you will need to reset the upload key through Google Play Console support.

## Local Properties

Create or update `android/local.properties` on the build machine:

```properties
sdk.dir=C:/Users/devaj/AppData/Local/Android/Sdk
SCIOBRAILLE_UPLOAD_STORE_FILE=C:/secure/path/sciobraille-upload.jks
SCIOBRAILLE_UPLOAD_STORE_PASSWORD=replace-me
SCIOBRAILLE_UPLOAD_KEY_ALIAS=sciobraille-upload
SCIOBRAILLE_UPLOAD_KEY_PASSWORD=replace-me
SCIOBRAILLE_BACKEND_URL=https://api.your-domain.example
```

`local.properties`, `*.jks`, and `*.keystore` are ignored by `.gitignore`.
For PKCS12 keystores, keep `SCIOBRAILLE_UPLOAD_KEY_PASSWORD` the same as
`SCIOBRAILLE_UPLOAD_STORE_PASSWORD`.

## Environment Variables

CI can provide the same values as environment variables:

- `SCIOBRAILLE_UPLOAD_STORE_FILE`
- `SCIOBRAILLE_UPLOAD_STORE_PASSWORD`
- `SCIOBRAILLE_UPLOAD_KEY_ALIAS`
- `SCIOBRAILLE_UPLOAD_KEY_PASSWORD`

## Build

```powershell
cd android
powershell.exe -ExecutionPolicy Bypass -File .\build_cached_gradle.ps1 :app:bundleRelease
```

Release builds now fail if upload-signing values are missing. This prevents a
debug-signed or unsigned release artifact from being mistaken for a Play upload.

After a successful release build, copy:

```text
android/app/build/outputs/bundle/release/app-release.aab
```

to:

```text
releases/SciobrailleScanner-release.aab
```
