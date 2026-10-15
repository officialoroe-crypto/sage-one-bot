import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'evolution_visual.dart';

enum EvolutionTransitionPhase {
  accelerate,
  concentrate,
  blackout,
  burst,
  reform,
  settle,
}

EvolutionTransitionPhase evolutionTransitionPhaseFor(double progress) {
  final value = progress.clamp(0.0, 1.0).toDouble();
  if (value < .18) return EvolutionTransitionPhase.accelerate;
  if (value < .32) return EvolutionTransitionPhase.concentrate;
  if (value < .43) return EvolutionTransitionPhase.blackout;
  if (value < .56) return EvolutionTransitionPhase.burst;
  if (value < .78) return EvolutionTransitionPhase.reform;
  return EvolutionTransitionPhase.settle;
}

class EvolutionTransition extends StatefulWidget {
  const EvolutionTransition({
    required this.from,
    required this.to,
    required this.child,
    this.duration = const Duration(milliseconds: 1800),
    this.onCompleted,
    super.key,
  });

  final EvolutionVisual from;
  final EvolutionVisual to;
  final Widget child;
  final Duration duration;
  final VoidCallback? onCompleted;

  @override
  State<EvolutionTransition> createState() => _EvolutionTransitionState();
}

class _EvolutionTransitionState extends State<EvolutionTransition>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: widget.duration)
      ..addStatusListener(_handleStatus)
      ..forward();
  }

  void _handleStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) {
      widget.onCompleted?.call();
    }
  }

  @override
  void didUpdateWidget(covariant EvolutionTransition oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.to.name != widget.to.name ||
        oldWidget.from.name != widget.from.name) {
      _controller
        ..duration = widget.duration
        ..forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller
      ..removeStatusListener(_handleStatus)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        widget.child,
        IgnorePointer(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, _) {
              final progress =
                  Curves.easeInOutCubic.transform(_controller.value);
              return CustomPaint(
                painter: _EvolutionTransitionPainter(
                  from: widget.from,
                  to: widget.to,
                  progress: progress,
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _EvolutionTransitionPainter extends CustomPainter {
  const _EvolutionTransitionPainter({
    required this.from,
    required this.to,
    required this.progress,
  });

  final EvolutionVisual from;
  final EvolutionVisual to;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final phase = evolutionTransitionPhaseFor(progress);
    final center = size.center(Offset.zero);
    final maxRadius = math.sqrt(
      size.width * size.width + size.height * size.height,
    );

    if (phase == EvolutionTransitionPhase.blackout ||
        phase == EvolutionTransitionPhase.burst) {
      final darkness = phase == EvolutionTransitionPhase.blackout
          ? ((progress - .32) / .11).clamp(0.0, 1.0).toDouble()
          : ((.56 - progress) / .13).clamp(0.0, 1.0).toDouble();
      canvas.drawRect(
        Offset.zero & size,
        Paint()..color = Colors.black.withValues(alpha: .82 * darkness),
      );
    }

    if (phase == EvolutionTransitionPhase.accelerate ||
        phase == EvolutionTransitionPhase.concentrate) {
      final energy = (progress / .32).clamp(0.0, 1.0).toDouble();
      _drawParticles(canvas, size, center, from.accent, energy, 28);
    }

    if (phase == EvolutionTransitionPhase.burst) {
      final burst = ((progress - .43) / .13).clamp(0.0, 1.0).toDouble();
      final radius = maxRadius * Curves.easeOut.transform(burst);
      final outerPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5 * (1 - burst) + .4
        ..color = to.accent.withValues(alpha: .85 * (1 - burst));
      final innerPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = outerPaint.strokeWidth
        ..color = from.accent.withValues(alpha: .38 * (1 - burst));
      canvas.drawCircle(center, radius, outerPaint);
      canvas.drawCircle(center, radius * .72, innerPaint);
    }

    if (phase == EvolutionTransitionPhase.reform ||
        phase == EvolutionTransitionPhase.settle) {
      final formation = ((progress - .56) / .44).clamp(0.0, 1.0).toDouble();
      _drawParticles(canvas, size, center, to.accent, formation, 32);
      final glow = math.sin(formation * math.pi);
      final glowRadius = math.min<double>(
        size.shortestSide * .24,
        180.0,
      );
      final glowPaint = Paint()
        ..color = to.accent.withValues(alpha: .10 * glow)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 28.0);
      canvas.drawCircle(center, glowRadius, glowPaint);
    }
  }

  void _drawParticles(
    Canvas canvas,
    Size size,
    Offset center,
    Color color,
    double energy,
    int count,
  ) {
    final paint = Paint()
      ..color = color.withValues(alpha: .12 + energy * .58);
    for (var i = 0; i < count; i++) {
      final angle = i * math.pi * 2 / count + energy * math.pi * 1.6;
      final baseRadius = size.shortestSide * (.10 + (i % 7) * .035);
      final radius = baseRadius + energy * size.shortestSide * .24;
      final x = center.dx + math.cos(angle) * radius;
      final y = center.dy + math.sin(angle) * radius;
      canvas.drawCircle(
        Offset(x, y),
        .7 + (i % 3) * .45 + energy * 1.1,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _EvolutionTransitionPainter oldDelegate) =>
      oldDelegate.from.name != from.name ||
      oldDelegate.to.name != to.name ||
      oldDelegate.progress != progress;
}
