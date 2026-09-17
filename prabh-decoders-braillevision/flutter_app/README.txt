Flutter app source for the on-device Android APK.

Steps (full detail in FLUTTER_APK_SETUP.md):
  1. git clone https://github.com/ultralytics/yolo-flutter-app
  2. cd yolo-flutter-app/example && flutter pub add ultralytics_yolo flutter_tts
  3. copy lib/main.dart and lib/braille_screen.dart (from here) into example/lib/
  4. copy model/best.tflite into example/android/app/src/main/assets/best.tflite
  5. flutter run --release   (then: flutter build apk --release)
  6. upload the .apk to a GitHub Release and link it in the root README.
