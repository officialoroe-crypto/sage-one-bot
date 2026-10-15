import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';
class CommandCenter extends StatefulWidget {
  const CommandCenter({required this.api, this.onCreate, super.key});
  final SageApi api;
  final VoidCallback? onCreate;

  @override
  State<CommandCenter> createState() => _CommandCenterState();
}

class _CommandCenterState extends State<CommandCenter>
    with SingleTickerProviderStateMixin {
  final _prompt = TextEditingController();
  String _status = 'Ready';
  String _worker = 'Checking worker…';
  String? _taskId;
  String? _result;
  bool _sending = false;
  Timer? _poller;
  late final AnimationController _orbController;

  @override
  void initState() {
    super.initState();
    _orbController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 5200),
    )..repeat();
    _loadWorker();
  }

  Future<void> _loadWorker() async {
    try {
      final data = await widget.api.workerHealth();
      final worker = Map<String, dynamic>.from(data['worker'] ?? {});
      if (!mounted) return;
      setState(() {
        _worker = worker['running'] == true ? 'Worker online' : 'Worker offline';
      });
    } catch (_) {
      if (mounted) setState(() => _worker = 'Worker unavailable');
    }
  }

  Future<void> _send() async {
    final prompt = _prompt.text.trim();
    if (prompt.isEmpty || _sending) return;

    setState(() {
      _sending = true;
      _status = 'Sending to SAGE Core…';
    });

    try {
      final result = await widget.api.submitBackground(prompt);
      final taskId = result['task_id'] ?? result['id'];
      if (taskId == null || taskId.toString().isEmpty) {
        throw Exception('SAGE did not return a task id.');
      }
      if (!mounted) return;

      setState(() {
        _taskId = taskId?.toString();
        _status = _taskId == null ? 'Accepted' : 'Queued • $_taskId!';
        _prompt.clear();
      });

      if (_taskId != null) _startPolling();
    } catch (error) {
      if (!mounted) return;
      setState(() => _status = 'Connection error');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _startPolling() {
    _poller?.cancel();
    _poller = Timer.periodic(const Duration(seconds: 3), (_) => _refreshTask());
    _refreshTask();
  }

  Future<void> _refreshTask() async {
    final taskId = _taskId;
    if (taskId == null) return;

    try {
      final task = await widget.api.task(taskId);
      if (!mounted) return;
      final status = (task['status'] ?? 'unknown').toString().toLowerCase();
      final value = task['result'] ?? task['error'];
      final terminal = {'completed', 'failed', 'cancelled', 'canceled'}.contains(status);

      setState(() {
        _status = terminal ? 'Task complete' : 'SAGE is working…';
        _result = value?.toString();
        _sending = !{'completed', 'failed', 'cancelled', 'canceled'}.contains(status);
      });

      if (!_sending) {
        _poller?.cancel();
        if (status == 'completed' && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Your task is complete. Open the result below.')),
          );
        }
      }
    } catch (_) {
      if (mounted) setState(() => _status = 'Waiting for SAGE Core…');
    }
  }

  @override
  void dispose() {
    _poller?.cancel();
    _orbController.dispose();
    _prompt.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: AnimatedBuilder(
          animation: _orbController,
          builder: (context, _) => CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 8),
                sliver: SliverToBoxAdapter(child: _header()),
              ),
              SliverToBoxAdapter(child: _orbSection()),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
                sliver: SliverToBoxAdapter(child: _commandBox()),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header() {
    return const Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('SAGE ONE', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: 1.8)),
              SizedBox(height: 3),
              Text('PERSONAL AI • EXECUTION PARTNER', style: TextStyle(fontSize: 8, letterSpacing: 1.2, color: SageTheme.textSecondary)),
            ],
          ),
        ),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('STAGE', style: TextStyle(fontSize: 8, letterSpacing: 1.5, color: SageTheme.textSecondary)),
            Text('EVOLUTION', style: TextStyle(fontSize: 9, letterSpacing: 1, color: SageTheme.cyan, fontWeight: FontWeight.w700)),
          ],
        ),
      ],
    );
  }

  Widget _orbSection() {
    final glow = .72 + (math.sin(_orbController.value * math.pi * 2) * .18);
    return Padding(
      padding: const EdgeInsets.fromLTRB(22, 34, 22, 8),
      child: Column(
        children: [
          const Text(
            'YOUR IDEAS. IN MOTION.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: SageTheme.cyan,
              fontSize: 10,
              letterSpacing: 3.2,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Good to see you, Nishant.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
              letterSpacing: -.6,
            ),
          ),
          const SizedBox(height: 7),
          const Text(
            'What would you like SAGE to help you accomplish?',
            textAlign: TextAlign.center,
            style: TextStyle(color: SageTheme.textSecondary, fontSize: 13, height: 1.5),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: 320,
            height: 320,
            child: CustomPaint(
              painter: _SageOrbPainter(
                intensity: glow,
                orbitAngle: _orbController.value * math.pi * 2,
              ),
              child: Center(
                child: Container(
                  width: 126,
                  height: 126,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const RadialGradient(
                      center: Alignment(-.35, -.42),
                      radius: .95,
                      colors: [
                        Color(0xFFB7F4FF),
                        Color(0xFF319BFF),
                        Color(0xFF1553D8),
                        Color(0xFF071A50),
                      ],
                      stops: [0, .25, .68, 1],
                    ),
                    border: Border.all(color: const Color(0xFF9BEFFF).withValues(alpha: .85), width: 1.2),
                    boxShadow: [
                      BoxShadow(color: SageTheme.cyan.withValues(alpha: .24 * glow), blurRadius: 42, spreadRadius: 3),
                    ],
                  ),
                  child: const Text(
                    'S',
                    style: TextStyle(
                      fontSize: 88,
                      height: 1,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                      shadows: [Shadow(color: Color(0xFF0A6BFF), blurRadius: 18)],
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 2),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
            decoration: BoxDecoration(
              color: SageTheme.cyan.withValues(alpha: .07),
              borderRadius: BorderRadius.circular(30),
              border: Border.all(color: SageTheme.cyan.withValues(alpha: .18)),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.circle, size: 6, color: SageTheme.success),
                SizedBox(width: 8),
                Text('SAGE CORE READY', style: TextStyle(fontSize: 9, letterSpacing: 1.8, color: SageTheme.textSecondary, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _commandBox() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _prompt,
          minLines: 3,
          maxLines: 6,
          decoration: const InputDecoration(
            hintText: 'Tell SAGE what you want done…',
            prefixIcon: Padding(
              padding: EdgeInsets.only(left: 14, right: 6),
              child: Icon(Icons.bolt, color: SageTheme.cyan),
            ),
            prefixIconConstraints: BoxConstraints(minWidth: 0, minHeight: 0),
            contentPadding: EdgeInsets.all(18),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(child: Text(_status, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11))),
            FilledButton.icon(
              onPressed: _sending ? null : _send,
              icon: Icon(_sending ? Icons.hourglass_top : Icons.arrow_upward),
              label: Text(_sending ? 'Working' : 'Execute'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Center(
          child: Text(
            _worker,
            style: const TextStyle(
              color: SageTheme.textSecondary,
              fontSize: 9,
            ),
          ),
        ),
        if (_result != null && _result!.isNotEmpty) ...[
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: SelectableText(_result!, style: const TextStyle(color: SageTheme.textPrimary, fontSize: 12, height: 1.45)),
            ),
          ),
        ],
      ],
    );
  }
}

class _SageOrbPainter extends CustomPainter {
  const _SageOrbPainter({required this.intensity, required this.orbitAngle});
  final double intensity;
  final double orbitAngle;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final shortest = size.shortestSide;
    final radius = shortest * .235;

    final halo = Paint()
      ..shader = RadialGradient(
        colors: [
          SageTheme.cyan.withValues(alpha: .19 * intensity),
          SageTheme.blue.withValues(alpha: .10 * intensity),
          Colors.transparent,
        ],
      ).createShader(Rect.fromCircle(center: center, radius: shortest * .49));
    canvas.drawCircle(center, shortest * .49, halo);

    // Fine orbital track: the signature SAGE ONE ring.
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(-.28);
    final orbitRect = Rect.fromCenter(
      center: Offset.zero,
      width: shortest * .91,
      height: shortest * .48,
    );
    final orbitPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.15
      ..color = SageTheme.cyan.withValues(alpha: .66 * intensity);
    canvas.drawOval(orbitRect, orbitPaint);
    final secondaryOrbit = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = .7
      ..color = Colors.white.withValues(alpha: .12);
    canvas.drawOval(orbitRect.inflate(7), secondaryOrbit);

    // A single golden coin moves around the orbit.
    final coinAngle = orbitAngle - math.pi / 2;
    final coinPosition = Offset(
      math.cos(coinAngle) * orbitRect.width / 2,
      math.sin(coinAngle) * orbitRect.height / 2,
    );
    final coinGlow = Paint()
      ..color = SageTheme.gold.withValues(alpha: .28)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 9);
    canvas.drawCircle(coinPosition, 13, coinGlow);
    final coinPaint = Paint()
      ..shader = const RadialGradient(
        colors: [Color(0xFFFFF0A6), Color(0xFFFFC247), Color(0xFFB86A12)],
      ).createShader(Rect.fromCircle(center: coinPosition, radius: 9));
    canvas.drawCircle(coinPosition, 9, coinPaint);
    canvas.drawCircle(
      coinPosition,
      6,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = const Color(0xFF8D4C0B),
    );
    canvas.restore();

    final sphereOutline = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = SageTheme.cyan.withValues(alpha: .38);
    canvas.drawCircle(center, radius + 2, sphereOutline);
  }

  @override
  bool shouldRepaint(covariant _SageOrbPainter oldDelegate) =>
      oldDelegate.intensity != intensity || oldDelegate.orbitAngle != orbitAngle;
}
