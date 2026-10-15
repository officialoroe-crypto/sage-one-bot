import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class VoiceCommandScreen extends StatefulWidget {
  const VoiceCommandScreen({required this.api, super.key});

  final SageApi api;

  @override
  State<VoiceCommandScreen> createState() => _VoiceCommandScreenState();
}

class _VoiceCommandScreenState extends State<VoiceCommandScreen> {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();
  Timer? _poller;

  String _transcript = '';
  String _status = 'Ready';
  String? _taskId;
  bool _available = false;
  bool _sending = false;
  bool _speaking = false;

  @override
  void initState() {
    super.initState();
    _initializeVoice();
  }

  Future<void> _initializeVoice() async {
    try {
      _available = await _speech.initialize(
        onStatus: (status) {
          if (!mounted) return;
          if (status == 'done' && !_sending) {
            setState(() => _status = 'Ready');
          }
        },
        onError: (error) {
          if (!mounted) return;
          setState(() => _status = 'Voice error: ${error.errorMsg}');
        },
      );
      await _tts.setLanguage('en-US');
      await _tts.setSpeechRate(0.48);
      await _tts.setPitch(1.0);
      if (mounted) {
        setState(() {
          _status = _available ? 'Tap the orb and speak' : 'Microphone unavailable';
        });
      }
    } catch (error) {
      if (mounted) setState(() => _status = 'Voice setup failed: $error');
    }
  }

  Future<void> _toggleListening() async {
    if (!_available || _sending) return;
    if (_speech.isListening) {
      await _speech.stop();
      if (mounted) setState(() => _status = 'Reviewing command…');
      return;
    }

    setState(() {
      _transcript = '';
      _status = 'Listening…';
    });
    await _speech.listen(
      onResult: _onSpeechResult,
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 4),
      partialResults: true,
    );
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    if (!mounted) return;
    setState(() {
      _transcript = result.recognizedWords;
      _status = result.finalResult ? 'Command captured' : 'Listening…';
    });
  }

  Future<void> _sendCommand() async {
    final command = _transcript.trim();
    if (command.isEmpty || _sending) return;
    await _speech.stop();

    setState(() {
      _sending = true;
      _status = 'Sending to SAGE…';
    });

    try {
      final response = await widget.api.submitCommand(command);
      final task = response['task'];
      final taskMap = task is Map ? Map<String, dynamic>.from(task) : null;
      _taskId = (taskMap?['id'] ?? response['task_id'])?.toString();
      if (_taskId == null || _taskId!.isEmpty) {
        throw Exception('SAGE did not return a task id.');
      }

      if (mounted) setState(() => _status = 'SAGE is working…');
      _poller?.cancel();
      _poller = Timer.periodic(const Duration(seconds: 2), (_) => _refreshTask());
      await _refreshTask();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _status = 'Command failed: $error';
      });
      await _speak('I could not send that command.');
    }
  }

  Future<void> _refreshTask() async {
    final taskId = _taskId;
    if (taskId == null) return;
    try {
      final task = await widget.api.task(taskId);
      final status = task['status']?.toString().toLowerCase() ?? 'pending';
      if (!mounted) return;

      if (status == 'completed') {
        final result = (task['result'] ?? '').toString().trim();
        _poller?.cancel();
        setState(() {
          _sending = false;
          _status = 'Complete';
        });
        if (result.isNotEmpty) await _speak(result);
      } else if ({'failed', 'cancelled', 'canceled'}.contains(status)) {
        final error = (task['error'] ?? 'SAGE could not complete the command.').toString();
        _poller?.cancel();
        setState(() {
          _sending = false;
          _status = 'Command failed';
        });
        await _speak(error);
      } else if (mounted) {
        setState(() => _status = 'SAGE is working…');
      }
    } catch (_) {
      // Polling is best-effort; the durable task remains the source of truth.
    }
  }

  Future<void> _speak(String text) async {
    final clean = text.trim();
    if (clean.isEmpty) return;
    try {
      if (mounted) setState(() => _speaking = true);
      await _tts.stop();
      await _tts.speak(clean.length > 1200 ? '${clean.substring(0, 1200)}…' : clean);
      if (mounted) setState(() => _speaking = false);
    } catch (_) {
      if (mounted) setState(() => _speaking = false);
    }
  }

  Future<void> _stopSpeaking() async {
    await _tts.stop();
    if (mounted) setState(() => _speaking = false);
  }

  @override
  void dispose() {
    _poller?.cancel();
    _speech.stop();
    _tts.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final listening = _speech.isListening;
    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      appBar: AppBar(
        title: const Text('SAGE Voice'),
        backgroundColor: Colors.transparent,
        actions: [
          if (_speaking)
            IconButton(onPressed: _stopSpeaking, icon: const Icon(Icons.stop_circle_outlined)),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: listening ? 180 : 150,
                      height: listening ? 180 : 150,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: SageTheme.cyan.withValues(alpha: listening ? .38 : .18),
                            blurRadius: listening ? 55 : 32,
                            spreadRadius: listening ? 10 : 2,
                          ),
                        ],
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            SageTheme.cyan.withValues(alpha: .95),
                            SageTheme.blue.withValues(alpha: .72),
                            SageTheme.violet.withValues(alpha: .7),
                          ],
                        ),
                      ),
                      child: Icon(
                        listening ? Icons.graphic_eq : Icons.mic_none,
                        size: 64,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      _status,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: SageTheme.textPrimary,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 28),
                      child: Text(
                        _transcript.isEmpty ? 'Voice commands use the same durable /command pipeline as text.' : _transcript,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: SageTheme.textSecondary, height: 1.45),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
              child: Column(
                children: [
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: (_available && !_sending) ? _toggleListening : null,
                      icon: Icon(listening ? Icons.stop : Icons.mic),
                      label: Text(listening ? 'Stop listening' : 'Speak to SAGE'),
                    ),
                  ),
                  if (_transcript.trim().isNotEmpty && !listening && !_sending) ...[
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.tonalIcon(
                        onPressed: _sendCommand,
                        icon: const Icon(Icons.arrow_upward),
                        label: const Text('Send command'),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
