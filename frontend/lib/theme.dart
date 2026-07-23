import 'package:flutter/material.dart';

/// 앱 전역 테마 — 화사하고 산뜻한 스타트업 무드.
/// 밝은 인디고 프라이머리 + 민트/핑크 악센트, 둥근 모서리, 넉넉한 여백.
class AppColors {
  static const primary = Color(0xFF5468FF); // 인디고
  static const primaryDark = Color(0xFF3B4BDB);
  static const accent = Color(0xFF22D3EE); // 민트/시안
  static const pink = Color(0xFFFF6B9A);
  static const bg = Color(0xFFF6F8FE); // 아주 옅은 블루-그레이
  static const surface = Colors.white;
  static const ink = Color(0xFF1B2030);
  static const muted = Color(0xFF7A839B);
  static const line = Color(0xFFE7EAF3);

  // 로그인 배경 애니메이션용 블롭 색
  static const blobA = Color(0xFF7B8CFF);
  static const blobB = Color(0xFF57E1F0);
  static const blobC = Color(0xFFFF9EC4);
}

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.light,
  ).copyWith(
    primary: AppColors.primary,
    secondary: AppColors.accent,
    surface: AppColors.surface,
    onSurface: AppColors.ink,
  );

  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.bg,
    splashFactory: InkSparkle.splashFactory,
    // Pretendard 를 기본 폰트로. CDN(@font-face)로 로드되며, 실패 시 시스템 폰트로 폴백.
    fontFamily: 'Pretendard',
    fontFamilyFallback: const [
      '-apple-system',
      'Apple SD Gothic Neo',
      'Malgun Gothic',
      'sans-serif',
    ],
  );

  final text = base.textTheme
      .apply(bodyColor: AppColors.ink, displayColor: AppColors.ink)
      .copyWith(
        headlineSmall: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: -0.5),
        titleLarge: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: -0.3),
        titleMedium: const TextStyle(fontWeight: FontWeight.w700),
        labelLarge: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.1),
      );

  return base.copyWith(
    textTheme: text,
    cardTheme: CardThemeData(
      elevation: 0,
      color: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      margin: const EdgeInsets.symmetric(vertical: 6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: AppColors.line),
      ),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
      foregroundColor: AppColors.ink,
      titleTextStyle: TextStyle(
          color: AppColors.ink, fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: -0.4),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontWeight: FontWeight.w700),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.6),
      ),
      labelStyle: const TextStyle(color: AppColors.muted),
      hintStyle: const TextStyle(color: AppColors.muted),
    ),
    chipTheme: base.chipTheme.copyWith(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      side: BorderSide.none,
      backgroundColor: const Color(0xFFEEF1FF),
      labelStyle: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.primaryDark),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.line, thickness: 1, space: 1),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? AppColors.primary : null),
      trackColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? AppColors.primary.withValues(alpha: 0.4) : null),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: AppColors.ink,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
  );
}

/// 브랜드 그라데이션(로고 배지·버튼 강조 등).
const kBrandGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [AppColors.primary, Color(0xFF7C4DFF)],
);
