import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'braille_camera_screen.dart';

late List<CameraDescription> cameras;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  cameras = await availableCameras();
  runApp(const BrailleVisionApp());
}

class BrailleVisionApp extends StatelessWidget {
  const BrailleVisionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BrailleVision',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const BrailleCameraScreen(),
    );
  }
}
