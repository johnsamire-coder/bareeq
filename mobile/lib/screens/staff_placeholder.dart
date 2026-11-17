import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/session.dart';
import '../widgets/common.dart';

/// Technician and manager screens arrive in step 12.
class StaffPlaceholder extends StatelessWidget {
  const StaffPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    final s = context.read<Session>();
    return Scaffold(
      appBar: AppBar(title: const Text('بريق')),
      body: EmptyState(
        icon: Icons.construction_rounded,
        text: 'أهلاً ${s.user?['full_name'] ?? ''}.\nشاشات الفني والمدير جاية قريب.',
        action: OutlinedButton(onPressed: s.logout, child: const Text('تسجيل خروج')),
      ),
    );
  }
}
