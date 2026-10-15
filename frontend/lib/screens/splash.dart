import 'dart:async';

import 'package:flutter/material.dart';

import '../theme/sage_theme.dart';

/// First visual entry point. The existing authentication/owner gate is mounted
/// only after the short branded transition completes.
class SageSplashScreen extends StatefulWidget {
  const SageSplashScreen({
    required this.child,
    super.key,
    this.duration = const Duration(milliseconds: 1800),
  });

  final Widget child;
  final Duration duration;

  @override
  State<SageSplashScreen> createState() => _SageSplashScreenState();
}

class _SageSplashScreenState extends State<SageSplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fade;
  Timer? _timer;
  bool _complete = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..forward();
    _fade = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
    _timer = Timer(widget.duration, () {
      if (mounted) setState(() => _complete = true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_complete) return widget.child;

    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -.22),
            radius: 1.15,
            colors: [
              Color(0xFF102C58),
              Color(0xFF061326),
              Color(0xFF020306),
            ],
            stops: [0, .52, 1],
          ),
        ),
        child: Center(
          child: FadeTransition(
            opacity: _fade,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedBuilder(
                  animation: _controller,
                  builder: (context, child) => Transform.scale(
                    scale: .92 + (_controller.value * .08),
                    child: child,
                  ),
                  child: SizedBox(
                    width: 156,
                    height: 156,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        const CustomPaint(
                          size: Size(156, 156),
                          painter: _SplashOrbitPainter(),
                        ),
                        Container(
                          width: 98,
                          height: 98,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: const RadialGradient(
                              center: Alignment(-.32, -.38),
                              radius: .9,
                              colors: [
                                Color(0xFFB9F5FF),
                                Color(0xFF329BFF),
                                Color(0xFF1768D8),
                                Color(0xFF071A45),
                              ],
                              stops: [0, .2, .48, 1],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: SageTheme.cyan.withValues(alpha: .34),
                                blurRadius: 38,
                                spreadRadius: 2,
                              ),
                            ],
                            border: Border.all(
                              color: SageTheme.cyan.withValues(alpha: .8),
                              width: 1.2,
                            ),
                          ),
                          child: const Text(
                            'S',
                            style: TextStyle(
                              fontSize: 66,
                              height: 1,
                              fontWeight: FontWeight.w500,
                              color: Colors.white,
                              shadows: [
                                Shadow(color: Color(0xFF146CFF), blurRadius: 18),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                const Text(
                  'SAGE ONE',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 25,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 7,
                  ),
                ),
                const SizedBox(height: 9),
                const Text(
                  'YOUR PERSONAL AI MENTOR & EXECUTION PARTNER',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: SageTheme.cyan,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.55,
                  ),
                ),
                const SizedBox(height: 42),
                SizedBox(
                  width: 92,
                  child: LinearProgressIndicator(
                    minHeight: 2,
                    backgroundColor: Colors.white.withValues(alpha: .09),
                    valueColor: const AlwaysStoppedAnimation(SageTheme.cyan),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

 
class _SplashOrbitPainter extends CustomPainter {
  const _SplashOrbitPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(-.32);
    final orbit = Rect.fromCenter(
      center: Offset.zero,
      width: size.width * .94,
      height: size.height * .48,
    );
    canvas.drawOval(
      orbit,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2
        ..color = SageTheme.cyan.withValues(alpha: .8),
    );
    canvas.drawOval(
      orbit.inflate(5),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = .65
        ..color = Colors.white.withValues(alpha: .22),
    );
    final coin = Offset(orbit.width * .37, -orbit.height * .33);
    canvas.drawCircle(
      coin,
      12,
      Paint()
        ..color = SageTheme.gold.withValues(alpha: .3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 7),
    );
    canvas.drawCircle(
      coin,
      8,
      Paint()
        ..shader = const RadialGradient(
          colors: [Color(0xFFFFF3B0), Color(0xFFFFC247), Color(0xFFB86A12)],
        ).createShader(Rect.fromCircle(center: coin, radius: 8)),
    );
    canvas.drawCircle(
      coin,
      5,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = const Color(0xFF8D4C0B),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _SplashOrbitPainter oldDelegate) => false;
}
