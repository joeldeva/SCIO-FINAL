// BrailleVision -- on-device Braille reader screen.
// Drop this into the Ultralytics yolo-flutter-app example app's lib/ folder and
// use it as the home screen (see FLUTTER_APK_SETUP.md).
//
// Model: your fine-tuned cell classifier, exported to TFLite and bundled at
//   android/app/src/main/assets/best.tflite   ->   referenced as modelPath: 'best'
// (the plugin auto-picks .tflite on Android / .mlpackage on iOS by filename).

import 'package:flutter/material.dart';
import 'package:ultralytics_yolo/ultralytics_yolo.dart';
import 'package:flutter_tts/flutter_tts.dart';

class _Det {
  final double cx, cy, h;
  final String label;
  _Det(this.cx, this.cy, this.h, this.label);
}

class BrailleScreen extends StatefulWidget {
  const BrailleScreen({super.key});
  @override
  State<BrailleScreen> createState() => _BrailleScreenState();
}

class _BrailleScreenState extends State<BrailleScreen> {
  final YOLOViewController _controller = YOLOViewController();
  final FlutterTts _tts = FlutterTts();
  final List<String> _history = []; // recent readings, for temporal voting
  String _current = '';
  String _lastSpoken = '';
  DateTime _lastSpeakAt = DateTime.fromMillisecondsSinceEpoch(0);

  @override
  void initState() {
    super.initState();
    _tts.setLanguage('en-US');
    _tts.setSpeechRate(0.5);
    _tts.setPitch(1.0);
  }

  // detections -> text in reading order (group lines by y, sort by x, gaps -> spaces)
  String _readingOrder(List<_Det> dets,
      {double lineTolFrac = 0.6, double spaceMult = 1.7}) {
    if (dets.isEmpty) return '';
    final hs = dets.map((d) => d.h).toList()..sort();
    final medH = hs[hs.length ~/ 2];
    final tol = medH * lineTolFrac;
    dets.sort((a, b) => a.cy.compareTo(b.cy));
    final lines = <List<_Det>>[];
    var cur = <_Det>[dets.first];
    for (final d in dets.skip(1)) {
      if ((d.cy - cur.last.cy).abs() <= tol) {
        cur.add(d);
      } else {
        lines.add(cur);
        cur = [d];
      }
    }
    lines.add(cur);
    final out = <String>[];
    for (final ln in lines) {
      ln.sort((a, b) => a.cx.compareTo(b.cx));
      final sb = StringBuffer(ln.first.label);
      for (var i = 1; i < ln.length; i++) {
        if (ln[i].cx - ln[i - 1].cx > medH * spaceMult) sb.write(' ');
        sb.write(ln[i].label);
      }
      out.add(sb.toString());
    }
    return out.join('\n');
  }

  String _mostCommon(List<String> xs) {
    final counts = <String, int>{};
    for (final x in xs) {
      counts[x] = (counts[x] ?? 0) + 1;
    }
    var best = '';
    var bn = -1;
    counts.forEach((k, v) {
      if (v > bn) {
        bn = v;
        best = k;
      }
    });
    return best;
  }

  void _onResults(List<YOLOResult> results) {
    final dets = <_Det>[];
    for (final r in results) {
      // YOLOResult exposes className, confidence, and boundingBox (a Rect).
      // If your plugin version names the box field differently (e.g. normalizedBox),
      // adjust the three reads below -- check the example app's lib/ for the type.
      final b = r.boundingBox;
      dets.add(_Det(b.center.dx, b.center.dy, b.height, r.className));
    }
    final reading = _readingOrder(dets);
    _history.add(reading);
    if (_history.length > 5) _history.removeAt(0);
    final stable = _mostCommon(_history);
    if (stable != _current && mounted) setState(() => _current = stable);

    final now = DateTime.now();
    if (stable.isNotEmpty &&
        stable != _lastSpoken &&
        now.difference(_lastSpeakAt).inMilliseconds > 1200) {
      _lastSpoken = stable;
      _lastSpeakAt = now;
      _tts.speak(stable.replaceAll('\n', '. '));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(
              child: YOLOView(
                modelPath: 'best', // android/app/src/main/assets/best.tflite
                task: YOLOTask.detect,
                controller: _controller,
                onResult: _onResults,
              ),
            ),
            Align(
              alignment: Alignment.bottomCenter,
              child: Container(
                width: double.infinity,
                color: Colors.black87,
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      _current.isEmpty ? 'Point the camera at Braille' : _current,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 34,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        ElevatedButton.icon(
                          onPressed: _current.isEmpty
                              ? null
                              : () => _tts.speak(_current.replaceAll('\n', '. ')),
                          icon: const Icon(Icons.volume_up),
                          label: const Text('Speak', style: TextStyle(fontSize: 18)),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 24, vertical: 14),
                          ),
                        ),
                        OutlinedButton.icon(
                          onPressed: () {
                            setState(() {
                              _current = '';
                              _history.clear();
                              _lastSpoken = '';
                            });
                          },
                          icon: const Icon(Icons.clear, color: Colors.white),
                          label: const Text('Clear',
                              style: TextStyle(fontSize: 18, color: Colors.white)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }
}
