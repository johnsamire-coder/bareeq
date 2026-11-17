import 'package:flutter/material.dart';

import 'close_day_screen.dart';
import 'technicians_screen.dart';
import 'zones_screen.dart';

/// Everything the manager manages. Grows with steps 14-16.
class AdminMenu extends StatelessWidget {
  const AdminMenu({super.key});

  @override
  Widget build(BuildContext context) {
    Widget item(IconData icon, String title, String sub, Widget page) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: Icon(icon),
            title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(sub),
            trailing: const Icon(Icons.chevron_left),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => page)),
          ),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      item(Icons.engineering_outlined, 'الفنيين', 'إضافة، إيقاف، المناطق، المواعيد، الإجازات', const TechniciansScreen()),
      item(Icons.map_outlined, 'المناطق', 'رسم الحدود على الخريطة، فتح وقفل', const ZonesScreen()),
      item(Icons.notifications_active_outlined, 'طلبات «بلغوني»', 'أماكن عايزة الخدمة ولسه مش عندنا', const DemandScreen()),
      item(Icons.thunderstorm_outlined, 'قفل يوم (الجو)', 'إلغاء حجوزات يوم لمنطقة أو للكل', const CloseDayScreen()),
    ]);
  }
}
