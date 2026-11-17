import 'package:flutter/material.dart';

/// Brand colors from design/brand-kit (05-Bareeq-Brand-Guide.pdf).
class BrandColors {
  static const layl = Color(0xFF0A2540); // ليل: main text and dark backgrounds
  static const mayya = Color(0xFF12B5CB); // مية: buttons
  static const lamaa = Color(0xFFFFC145); // لمعة: the star, use sparingly
  static const razaz = Color(0xFFD4F2F6); // رذاذ: light backgrounds
  static const sahab = Color(0xFFF6FAFB); // سحاب: page background
  static const muted = Color(0xFF5B6B7C);
  static const line = Color(0xFFE2E9EE);
  static const danger = Color(0xFFC62828);
  static const good = Color(0xFF2E7D32);
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: BrandColors.mayya,
    primary: BrandColors.mayya,
    onPrimary: Colors.white,
    secondary: BrandColors.layl,
    surface: Colors.white,
    onSurface: BrandColors.layl,
    error: BrandColors.danger,
  );
  final base = ThemeData(useMaterial3: true, colorScheme: scheme, fontFamily: 'Cairo');
  return base.copyWith(
    scaffoldBackgroundColor: BrandColors.sahab,
    textTheme: base.textTheme.apply(bodyColor: BrandColors.layl, displayColor: BrandColors.layl),
    appBarTheme: const AppBarTheme(
      backgroundColor: BrandColors.sahab,
      foregroundColor: BrandColors.layl,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(fontFamily: 'Cairo', fontSize: 18, fontWeight: FontWeight.w700, color: BrandColors.layl),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: BrandColors.mayya,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontFamily: 'Cairo', fontSize: 16, fontWeight: FontWeight.w700),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: BrandColors.layl,
        minimumSize: const Size.fromHeight(48),
        side: const BorderSide(color: BrandColors.line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontFamily: 'Cairo', fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: BrandColors.line)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: BrandColors.line)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: BrandColors.mayya, width: 2)),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: BrandColors.line)),
    ),
    navigationBarTheme: const NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: BrandColors.razaz,
    ),
  );
}
