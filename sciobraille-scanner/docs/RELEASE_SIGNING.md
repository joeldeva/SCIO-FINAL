# Sciobraille Release Signing

The project supports Play upload signing without storing passwords or keystores
in source control.

## Upload key ownership

The development APK from GitHub Actions uses a temporary debug key. No production
upload keystore or passwords were provided to this development environment, and
no production-signed APK or AAB is claimed. Use the project's existing upload key
on your trusted build machine. Historical notes refer to a key on the original
developer's Windows computer; that does not make it available here.

Do not upload `local.properties` or the `.jks` file to GitHub. Keep the keystore
and its passwords backed up securely. Debug builds from different CI machines
may use different keys; Android cannot update an installed app signed by a
different key. Uninstalling the old build deletes local history and progress.

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

```sh
cd sciobraille-scanner/android
./gradlew :app:bundleRelease
```

On Windows use `gradlew.bat :app:bundleRelease`. Configure an HTTPS backend for
online production use. The public service's authentication, request limits and
translation provider credentials must be configured before release.

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
