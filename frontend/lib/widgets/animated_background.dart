import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme.dart';

/// 로그인 화면 배경: 은은한 그라데이션 위로 소프트 블롭이 천천히 떠다니는 애니메이션.
/// 외부 패키지 없이 CustomPainter 로 구현.
class AnimatedBackground extends StatefulWidget {
  final Widget child;
  const AnimatedBackground({super.key, required this.child});

  @override
  State<AnimatedBackground> createState() => _AnimatedBackgroundState();
}

class _AnimatedBackgroundState extends State<AnimatedBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(seconds: 18))..repeat();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFFEFF2FF), Color(0xFFF7F0FF), Color(0xFFFDF1F7)],
            ),
          ),
        ),
        AnimatedBuilder(
          animation: _c,
          builder: (context, _) => CustomPaint(painter: _BlobPainter(_c.value)),
        ),
        widget.child,
      ],
    );
  }
}

class _Blob {
  final Color color;
  final double radius; // 화면 짧은 변 기준 비율
  final double cx, cy; // 중심 기준 위치
  final double ax, ay; // 이동 진폭
  final double phase;
  const _Blob(this.color, this.radius, this.cx, this.cy, this.ax, this.ay, this.phase);
}

const _blobs = [
  _Blob(AppColors.blobA, 0.42, 0.22, 0.28, 0.06, 0.05, 0.0),
  _Blob(AppColors.blobB, 0.36, 0.82, 0.30, 0.05, 0.07, 1.6),
  _Blob(AppColors.blobC, 0.40, 0.68, 0.82, 0.07, 0.05, 3.1),
  _Blob(AppColors.blobA, 0.30, 0.15, 0.85, 0.05, 0.06, 4.4),
];

class _BlobPainter extends CustomPainter {
  final double t;
  _BlobPainter(this.t);

  @override
  void paint(Canvas canvas, Size size) {
    final short = math.min(size.width, size.height);
    const tau = 2 * math.pi;
    for (final b in _blobs) {
      final dx = math.sin(tau * t + b.phase) * b.ax * size.width;
      final dy = math.cos(tau * t + b.phase) * b.ay * size.height;
      final center = Offset(b.cx * size.width + dx, b.cy * size.height + dy);
      final r = b.radius * short;
      final paint = Paint()
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 60)
        ..shader = RadialGradient(
          colors: [b.color.withValues(alpha: 0.55), b.color.withValues(alpha: 0.0)],
        ).createShader(Rect.fromCircle(center: center, radius: r));
      canvas.drawCircle(center, r, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _BlobPainter old) => old.t != t;
}
