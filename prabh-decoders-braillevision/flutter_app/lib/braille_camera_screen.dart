import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;
import 'main.dart';

class BrailleCameraScreen extends StatefulWidget {
  const BrailleCameraScreen({super.key});

  @override
  State<BrailleCameraScreen> createState() => _BrailleCameraScreenState();
}

class _BrailleCameraScreenState extends State<BrailleCameraScreen> {
  late CameraController _camera;
  final FlutterTts _tts = FlutterTts();
  bool _isInitialized = false;
  bool _isProcessing = false;
  String _reading = '';
  String _serverUrl = 'http://192.168.1.100:5000'; // Change to your laptop IP
  Uint8List? _annotatedImage;
  final TextEditingController _urlController = TextEditingController();
  bool _isCapturing = false;
  Timer? _captureTimer;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _tts.setLanguage('en-US');
    _tts.setSpeechRate(0.45);
    _urlController.text = _serverUrl;
  }

  Future<void> _initCamera() async {
    _camera = CameraController(
      cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      ),
      ResolutionPreset.high,
      enableAudio: false,
    );
    await _camera.initialize();
    if (mounted) setState(() => _isInitialized = true);
  }

  Future<void> _captureAndDetect() async {
    if (_isProcessing || !_camera.value.isInitialized) return;
    setState(() => _isProcessing = true);

    try {
      final file = await _camera.takePicture();
      final bytes = await file.readAsBytes();

      // Send to Python backend
      final uri = Uri.parse('$_serverUrl/detect');
      final request = http.MultipartRequest('POST', uri)
        ..files.add(http.MultipartFile.fromBytes('image', bytes, filename: 'capture.jpg'));

      final response = await request.send().timeout(const Duration(seconds: 10));
      final body = await response.stream.bytesToString();
      final json = jsonDecode(body);

      if (mounted) {
        setState(() {
          _reading = json['text'] ?? '';
          if (json['annotated_image'] != null) {
            _annotatedImage = base64Decode(json['annotated_image']);
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _reading = 'Error: $e\nCheck server URL and connection.');
      }
    }

    setState(() => _isProcessing = false);
  }

  void _toggleContinuousCapture() {
    if (_isCapturing) {
      _captureTimer?.cancel();
      setState(() => _isCapturing = false);
    } else {
      setState(() => _isCapturing = true);
      _captureTimer = Timer.periodic(
        const Duration(seconds: 2),
        (_) => _captureAndDetect(),
      );
      _captureAndDetect(); // Capture immediately
    }
  }

  void _speak() {
    if (_reading.isNotEmpty) {
      _tts.speak(_reading.replaceAll('\n', '. '));
    }
  }

  void _updateServer() {
    setState(() => _serverUrl = _urlController.text.trim());
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Server: $_serverUrl')),
    );
  }

  void _showSettings() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Server URL', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(
                hintText: 'http://192.168.1.100:5000',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _updateServer, child: const Text('Save')),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _camera.dispose();
    _tts.stop();
    _captureTimer?.cancel();
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('👁️ BrailleVision'),
        backgroundColor: Colors.black87,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettings,
          ),
        ],
      ),
      body: !_isInitialized
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Camera preview or annotated result
                Expanded(
                  flex: 3,
                  child: Stack(
                    children: [
                      if (_annotatedImage != null)
                        Center(child: Image.memory(_annotatedImage!, fit: BoxFit.contain))
                      else
                        CameraPreview(_camera),
                      if (_isProcessing)
                        const Center(
                          child: CircularProgressIndicator(color: Colors.greenAccent),
                        ),
                    ],
                  ),
                ),
                // Reading display
                Container(
                  width: double.infinity,
                  color: Colors.black87,
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _reading.isEmpty ? 'Point camera at Braille and tap Capture' : _reading,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: _reading.isEmpty ? Colors.grey : Colors.white,
                          fontSize: _reading.isEmpty ? 16 : 28,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.5,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          ElevatedButton.icon(
                            onPressed: _isProcessing ? null : _captureAndDetect,
                            icon: const Icon(Icons.camera_alt, size: 28),
                            label: const Text('Capture', style: TextStyle(fontSize: 16)),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                              backgroundColor: Colors.indigo,
                            ),
                          ),
                          OutlinedButton.icon(
                            onPressed: _toggleContinuousCapture,
                            icon: Icon(
                              _isCapturing ? Icons.stop : Icons.play_arrow,
                              color: _isCapturing ? Colors.red : Colors.greenAccent,
                              size: 28,
                            ),
                            label: Text(
                              _isCapturing ? 'Stop' : 'Auto',
                              style: TextStyle(
                                fontSize: 16,
                                color: _isCapturing ? Colors.red : Colors.greenAccent,
                              ),
                            ),
                          ),
                          ElevatedButton.icon(
                            onPressed: _reading.isEmpty ? null : _speak,
                            icon: const Icon(Icons.volume_up, size: 28),
                            label: const Text('Speak', style: TextStyle(fontSize: 16)),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
