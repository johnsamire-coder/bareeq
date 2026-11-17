import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../widgets/common.dart';

/// Status pill colors.
Widget statusPill(Map o) {
  final s = '${o['status']}';
  const active = {'confirmed', 'on_the_way', 'arrived', 'in_progress'};
  const bad = {
    'cancelled_by_customer',
    'cancelled_by_company',
    'car_not_found',
    'expired',
  };
  if (s == 'completed') {
    return Pill(
      '${o['status_label']}',
      color: const Color(0xFFE3F4E5),
      textColor: BrandColors.good,
    );
  }
  if (bad.contains(s)) {
    return Pill(
      '${o['status_label']}',
      color: const Color(0xFFF1F3F5),
      textColor: BrandColors.muted,
    );
  }
  if (active.contains(s)) return Pill('${o['status_label']}');
  return Pill(
    '${o['status_label']}',
    color: const Color(0xFFFFF3D6),
    textColor: const Color(0xFF8A5A00),
  );
}
