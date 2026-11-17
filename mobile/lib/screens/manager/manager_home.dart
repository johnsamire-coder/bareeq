import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import 'admin_menu.dart';
import 'inbox_screen.dart';
import 'today_screen.dart';

/// Manager app: today's work, the inbox (things waiting), management, account.
class ManagerHome extends StatefulWidget {
  const ManagerHome({super.key});

  @override
  State<ManagerHome> createState() => _ManagerHomeState();
}

class _ManagerHomeState extends State<ManagerHome> {
  int _tab = 0;
  int _waiting = 0;

  @override
  void initState() {
    super.initState();
    _refreshBadge();
  }

  Future<void> _refreshBadge() async {
    try {
      final r = Map<String, dynamic>.from(await context.read<Session>().api.get('manage/inbox/'));
      const keys = ['instapay_to_review', 'refunds_due', 'closings_to_confirm', 'bad_ratings', 'damage_reports'];
      if (mounted) setState(() => _waiting = keys.fold(0, (s, k) => s + (r[k] as int)));
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    const titles = ['شغل اليوم', 'المتابعة', 'الإدارة', 'حسابي'];
    return Scaffold(
      appBar: AppBar(title: Text(titles[_tab]), automaticallyImplyLeading: false),
      body: SafeArea(
        child: IndexedStack(index: _tab, children: [
          const TodayScreen(),
          InboxScreen(onChanged: _refreshBadge),
          const AdminMenu(),
          ListView(padding: const EdgeInsets.all(16), children: [
            Card(
              child: ListTile(
                leading: const CircleAvatar(child: Icon(Icons.admin_panel_settings_outlined)),
                title: Text('${s.user?['full_name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${s.user?['phone'] ?? ''}', textDirection: TextDirection.ltr, textAlign: TextAlign.right),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(onPressed: s.logout, icon: const Icon(Icons.logout), label: const Text('تسجيل خروج')),
          ]),
        ]),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) {
          setState(() => _tab = i);
          _refreshBadge();
        },
        destinations: [
          const NavigationDestination(icon: Icon(Icons.today_outlined), label: 'اليوم'),
          NavigationDestination(
            icon: Badge(isLabelVisible: _waiting > 0, label: Text('$_waiting'), child: const Icon(Icons.inbox_outlined)),
            label: 'المتابعة',
          ),
          const NavigationDestination(icon: Icon(Icons.tune_rounded), label: 'الإدارة'),
          const NavigationDestination(icon: Icon(Icons.person_outline), label: 'حسابي'),
        ],
      ),
    );
  }
}
