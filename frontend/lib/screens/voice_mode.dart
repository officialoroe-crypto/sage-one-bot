import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class SageVoiceScreen extends StatefulWidget {
  const SageVoiceScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<SageVoiceScreen> createState() => _SageVoiceScreenState();
}

class _SageVoiceScreenState extends State<SageVoiceScreen> {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();
  final _command = TextEditingController();

  Timer? _poller;
  bool _ready = false;
  bool _listening = false;
  bool _processing = false;
  bool _speaking = false;
  bool _wakeMode = true;
  String _status = 'INITIALIZING';
  String _localeId = 'en_US';
  String? _taskId;
  String? _result;

  @override
  void initState() {
    super.initState();
    _initVoice();
  }

  @override
  void dispose() {
    _poller?.cancel();
    _speech.stop();
    _tts.stop();
    _command.dispose();
    super.dispose();
  }

  Future<void> _initVoice() async {
    try {
      final available = await _speech.initialize(
        onStatus: _onSpeechStatus,
        onError: (error) {
          if (!mounted) return;
          setState(() {
            _listening = false;
            _status = 'VOICE ERROR';
          });
          _snack(error.errorMsg);
          if (_wakeMode && _ready && !_processing) {
            _restartWakeListening();
          }
        },
      );

      if (!available) {
        if (mounted) setState(() => _status = 'MIC UNAVAILABLE');
        return;
      }

      final locales = await _speech.locales();
      final nepali = locales.where((x) {
        final id = x.localeId.toLowerCase();
        return id == 'ne_np' || id.startsWith('ne_');
      }).toList();

      if (nepali.isNotEmpty) _localeId = nepali.first.localeId;

      await _tts.setSpeechRate(.46);
      await _tts.setVolume(.95);
      await _tts.setPitch(1.0);
      _tts.setStartHandler(() {
        if (mounted) setState(() => _speaking = true);
      });
      _tts.setCompletionHandler(() {
        if (mounted) setState(() => _speaking = false);
      });
      _tts.setCancelHandler(() {
        if (mounted) setState(() => _speaking = false);
      });

      if (!mounted) return;
      setState(() {
        _ready = true;
        _status = _wakeMode ? 'SAY SAGE TO WAKE' : 'READY';
      });

      if (_wakeMode) await _startListening();
    } catch (error) {
      if (mounted) setState(() => _status = 'VOICE SETUP FAILED');
      _snack(error.toString());
    }
  }

  void _onSpeechStatus(String status) {
    if (!mounted) return;

    if (status == 'listening') {
      setState(() {
        _listening = true;
        _status = _wakeMode ? 'LISTENING FOR SAGE' : 'LISTENING';
      });
      return;
    }

    if (status == 'done' || status == 'notListening') {
      setState(() => _listening = false);
      if (_wakeMode && _ready && !_processing && !_speaking) {
        _restartWakeListening();
      } else if (!_processing && !_speaking) {
        setState(() => _status = 'READY');
      }
    }
  }

  Future<void> _restartWakeListening() async {
    await Future<void>.delayed(const Duration(milliseconds: 180));
    if (!mounted || !_wakeMode || !_ready || _processing || _speaking) return;
    await _startListening();
  }

  Future<void> _startListening() async {
    if (!_ready || _processing || _speaking || _speech.isListening) return;
    try {
      await _speech.listen(
        localeId: _localeId,
        listenFor: const Duration(seconds: 30),
        pauseFor: const Duration(seconds: 3),
        partialResults: true,
        onResult: _onSpeechResult,
      );
    } catch (error) {
      if (mounted) _snack(error.toString());
    }
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    if (!mounted) return;

    final transcript = result.recognizedWords.trim();
    setState(() {
      _command.text = transcript;
      _command.selection =
          TextSelection.collapsed(offset: _command.text.length);
    });

    if (!result.finalResult) return;

    if (_wakeMode) {
      final normalized = transcript.toLowerCase();
      final wakeIndex = normalized.indexOf('sage');
      if (wakeIndex < 0) return;

      final command = transcript.substring(wakeIndex + 4).trim();
      if (command.isEmpty) {
        _speech.stop();
        _speak('Yes. What would you like me to do?').then((_) {
          if (mounted && _wakeMode) _restartWakeListening();
        });
        return;
      }
      _command.text = command;
    }

    _speech.stop();
    _submit();
  }

  Future<void> _toggleWakeMode() async {
    final next = !_wakeMode;
    setState(() => _wakeMode = next);
    await _speech.stop();

    if (next) {
      setState(() => _status = 'SAY SAGE TO WAKE');
      await _restartWakeListening();
    } else if (mounted) {
      setState(() => _status = 'READY');
    }
  }

  Future<void> _submit() async {
    final prompt = _command.text.trim();
    if (prompt.isEmpty || _processing) return;

    await _speech.stop();
    setState(() {
      _processing = true;
      _listening = false;
      _status = 'EXECUTING';
      _result = null;
    });

    try {
      final response = await widget.api.submitBackground(prompt);
      final task = response['task'];
      final rawId = response['task_id'] ??
          (task is Map ? (task['id'] ?? task['task_id']) : null);
      final taskId = rawId?.toString();

      if (taskId == null || taskId.isEmpty) {
        throw Exception('SAGE did not return a task id.');
      }

      _taskId = taskId;
      _poller?.cancel();
      _poller = Timer.periodic(
        const Duration(seconds: 2),
        (_) => _poll(),
      );
      await _poll();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _processing = false;
        _status = 'ERROR';
      });
      await _speak('I could not execute that command. Please try again.');
      _snack(error.toString());
      if (_wakeMode) await _restartWakeListening();
    }
  }

  Future<void> _poll() async {
    final id = _taskId;
    if (id == null) return;

    try {
      final task = await widget.api.task(id);
      final state =
          (task['status'] ?? task['state'] ?? '').toString().toUpperCase();
      const terminal = {'COMPLETED', 'FAILED', 'CANCELLED', 'CANCELED'};

      if (!terminal.contains(state)) return;

      _poller?.cancel();
      final raw = task['result'] ?? task['output'] ?? task['message'];
      final result = raw?.toString().trim();

      if (!mounted) return;
      setState(() {
        _processing = false;
        _status = state == 'COMPLETED' ? 'COMPLETE' : state;
        _result = result?.isNotEmpty == true ? result : null;
      });

      if (state == 'COMPLETED') {
        var spoken = 'Your task is complete.';
        if (result != null && result.isNotEmpty) {
          spoken += ' ${result.length > 160 ? result.substring(0, 160) : result}';
        }
        await _speak(spoken);
      } else {
        await _speak('The task ended with status $state.');
      }

      if (_wakeMode && mounted) await _restartWakeListening();
    } catch (error) {
      _poller?.cancel();
      if (mounted) {
        setState(() {
          _processing = false;
          _status = 'ERROR';
        });
        _snack(error.toString());
        if (_wakeMode) await _restartWakeListening();
      }
    }
  }

  Future<void> _speak(String text) async {
    try {
      await _tts.stop();
      await _tts.setLanguage(
        _localeId.toLowerCase().startsWith('ne') ? 'ne-NP' : 'en-US',
      );
      await _tts.speak(text);
    } catch (_) {}
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = _listening || _processing || _speaking;
    final accent = _status == 'COMPLETE'
        ? SageTheme.success
        : (_status == 'ERROR' || _status.contains('FAILED')
            ? SageTheme.failure
            : SageTheme.cyan);

    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      appBar: AppBar(
        title: const Text('SAGE VOICE'),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            tooltip: _wakeMode
                ? 'Disable SAGE wake mode'
                : 'Enable SAGE wake mode',
            onPressed: _ready && !_processing ? _toggleWakeMode : null,
            icon: Icon(_wakeMode ? Icons.hearing : Icons.hearing_disabled),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              color: SageTheme.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: accent.withValues(alpha: .22)),
              boxShadow: active
                  ? [
                      BoxShadow(
                        color: accent.withValues(alpha: .14),
                        blurRadius: 30,
                        spreadRadius: 2,
                      ),
                    ]
                  : null,
            ),
            child: Column(
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 220),
                  width: 116,
                  height: 116,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: accent.withValues(alpha: .06),
                    border: Border.all(color: accent.withValues(alpha: .42)),
                    boxShadow: [
                      BoxShadow(
                        color: accent.withValues(
                          alpha: active ? .22 : .08,
                        ),
                        blurRadius: active ? 34 : 18,
                        spreadRadius: active ? 4 : 1,
                      ),
                    ],
                  ),
                  child: Icon(
                    _speaking
                        ? Icons.volume_up
                        : (_listening ? Icons.graphic_eq : Icons.mic_none),
                    size: 44,
                    color: accent,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  _status,
                  style: TextStyle(
                    color: accent,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 7),
                Text(
                  _wakeMode
                      ? 'SAGE is listening for its name. Say “Hey SAGE”, “SAGE”, or “Hello SAGE”, then your command.'
                      : 'Speak naturally. SAGE captures the command, executes it, and can speak the result back.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: SageTheme.textSecondary,
                    fontSize: 11,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          TextField(
            controller: _command,
            minLines: 3,
            maxLines: 6,
            decoration: const InputDecoration(
              labelText: 'Voice command',
              hintText: 'Say what you want SAGE to do…',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _processing ? null : _submit,
            icon: const Icon(Icons.play_arrow),
            label: const Text('EXECUTE COMMAND'),
          ),
          const SizedBox(height: 9),
          OutlinedButton.icon(
            onPressed: _processing ? null : _startListening,
            icon: const Icon(Icons.mic),
            label: const Text('START LISTENING'),
          ),
          const SizedBox(height: 14),
          Card(
            child: ListTile(
              leading: const Icon(Icons.translate, color: SageTheme.violet),
              title: const Text('Nepali-first voice'),
              subtitle: Text(
                _localeId.toLowerCase().startsWith('ne')
                    ? 'Nepali recognizer selected.'
                    : 'Nepali is preferred when the device exposes a recognizer; otherwise English is used.',
                style: const TextStyle(
                  fontSize: 10,
                  color: SageTheme.textSecondary,
                ),
              ),
            ),
          ),
          if (_result != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: SageTheme.surface,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: accent.withValues(alpha: .22)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _status == 'COMPLETE'
                        ? 'YOUR TASK IS COMPLETE'
                        : 'TASK RESULT',
                    style: TextStyle(
                      color: accent,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.3,
                    ),
                  ),
                  const SizedBox(height: 9),
                  SelectableText(
                    _result!,
                    style: const TextStyle(
                      fontSize: 12,
                      height: 1.45,
                      color: SageTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 9),
                  OutlinedButton.icon(
                    onPressed: () => _speak(_result!),
                    icon: const Icon(Icons.volume_up, size: 16),
                    label: const Text('SPEAK RESULT'),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
