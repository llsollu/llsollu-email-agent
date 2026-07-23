import 'package:flutter/material.dart';

/// 앱 전역 테마 — 참조 대시보드(Office 블루, 플랫·깔끔) 무드.
/// 밝은 회색 배경 + 흰 카드 + 옅은 보더 + 8px 라운드, Office 블루 포인트.
class AppColors {
  static const primary = Color(0xFF0078D4); // Office 블루
  static const primaryDark = Color(0xFF106EBE);
  static const success = Color(0xFF107C10);
  static const warning = Color(0xFFFF8C00);
  static const danger = Color(0xFFD13438);
  static const storyboard = Color(0xFF6B46C1);

  static const bg = Color(0xFFF9FAFB); // gray-50
  static const surface = Colors.white;
  static const gray100 = Color(0xFFF3F4F6);
  static const line = Color(0xFFE5E7EB); // gray-200
  static const ink = Color(0xFF111827); // gray-900
  static const muted = Color(0xFF4B5563); // gray-600

  // 로그인 배경 애니메이션 블롭(그대로 유지)
  static const blobA = Color(0xFF7B8CFF);
  static const blobB = Color(0xFF57E1F0);
  static const blobC = Color(0xFFFF9EC4);
}

const double kRadius = 8;

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.light,
  ).copyWith(
    primary: AppColors.primary,
    surface: AppColors.surface,
    onSurface: AppColors.ink,
    error: AppColors.danger,
  );

  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.bg,
    // Pretendard 를 CDN 으로 로드해 사용(웹). 참조의 Segoe UI 처럼 깔끔한 산세리프 무드.
    fontFamily: 'Pretendard',
    fontFamilyFallback: const [
      'Segoe UI',
      '-apple-system',
      'Apple SD Gothic Neo',
      'Malgun Gothic',
      'sans-serif',
    ],
  );

  final text = base.textTheme
      .apply(bodyColor: AppColors.ink, displayColor: AppColors.ink)
      .copyWith(
        headlineSmall: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: -0.2),
        titleLarge: const TextStyle(fontWeight: FontWeight.w600, letterSpacing: -0.2),
        titleMedium: const TextStyle(fontWeight: FontWeight.w600),
        labelLarge: const TextStyle(fontWeight: FontWeight.w600),
      );

  RoundedRectangleBorder r([double radius = kRadius, Color? side]) => RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(radius),
        side: side != null ? BorderSide(color: side) : BorderSide.none,
      );

  return base.copyWith(
    textTheme: text,
    cardTheme: CardThemeData(
      elevation: 0,
      color: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      margin: EdgeInsets.zero,
      shape: r(kRadius, AppColors.line),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
      foregroundColor: AppColors.ink,
      titleTextStyle: TextStyle(
          color: AppColors.ink, fontSize: 18, fontWeight: FontWeight.w600, letterSpacing: -0.2),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: r(kRadius),
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        shape: r(kRadius),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.ink,
        side: const BorderSide(color: AppColors.line),
        shape: r(kRadius),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(kRadius), borderSide: const BorderSide(color: AppColors.line)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(kRadius), borderSide: const BorderSide(color: AppColors.line)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(kRadius), borderSide: const BorderSide(color: AppColors.primary, width: 1.5)),
      labelStyle: const TextStyle(color: AppColors.muted),
      hintStyle: const TextStyle(color: AppColors.muted),
    ),
    chipTheme: base.chipTheme.copyWith(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      side: BorderSide.none,
      backgroundColor: const Color(0xFFE8F4FD),
      labelStyle: const TextStyle(fontWeight: FontWeight.w500, color: Color(0xFF0563A5), fontSize: 11),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.line, thickness: 1, space: 1),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: AppColors.ink,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kRadius)),
    ),
    popupMenuTheme: PopupMenuThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kRadius), side: const BorderSide(color: AppColors.line)),
      color: AppColors.surface,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kRadius)),
    ),
  );
}

/// 브랜드 포인트(로고 배지 등) — Office 블루 톤.
const kBrandGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [AppColors.primary, AppColors.primaryDark],
);
