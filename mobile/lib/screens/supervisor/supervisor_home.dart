import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';
import '../manager/inbox_screen.dart';
import '../manager/live_map_screen.dart';
import '../manager/today_screen.dart';

/// Supervisor (phase 4): the work of his zones only — today's jobs, the map,
/// moving a job to another technician, bad ratings and damage reports.
/// No money, prices, settings or closings.
class SupervisorHome extends StatefulWidget {
  const SupervisorHome({super.key});

  @override
  State<SupervisorHome> createState() => _SupervisorHomeState();
}

class _SupervisorHomeState extends State<SupervisorHome> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    const titles = ['شغل اليوم', 'المتابعة', 'حسابي'];
    Widget link(IconData icon, String label, Widget page) => Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon),
        title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        trailing: const Icon(Icons.chevron_left),
        onTap: () =>
            Navigator.push(context, MaterialPageRoute(builder: (_) => page)),
      ),
    );
    return Scaffold(
      appBar: AppBar(
        title: Text(titles[_tab]),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: IndexedStack(
          index: _tab,
          children: [
            const TodayScreen(),
            ListView(
              padding: const EdgeInsets.all(16),
              children: [
                link(Icons.map_outlined, 'خريطة اليوم', const LiveMapScreen()),
                link(
                  Icons.star_half_rounded,
                  'تقييمات وحشة',
                  const BadRatingsScreen(),
                ),
                link(
                  Icons.report_gmailerrorred,
                  'بلاغات الضرر',
                  const DamageReportsScreen(),
                ),
              ],
            ),
            ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: ListTile(
                    leading: const CircleAvatar(
                      child: Icon(Icons.supervisor_account),
                    ),
                    title: Text('${s.user?['full_name'] ?? ''}'),
                    subtitle: const Text('مشرف'),
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: s.logout,
                  icon: const Icon(Icons.logout),
                  label: const Text('تسجيل خروج'),
                ),
                const SizedBox(height: 8),
                const Muted(
                  'بتشوف شغل مناطقك بس. الفلوس والأسعار والإعدادات عند المدير.',
                ),
              ],
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today), label: 'اليوم'),
          NavigationDestination(
            icon: Icon(Icons.inbox_outlined),
            label: 'المتابعة',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'حسابي',
          ),
        ],
      ),
    );
  }
}
