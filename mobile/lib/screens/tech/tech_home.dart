import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../orders/status.dart';
import 'closing_screen.dart';
import 'job_detail_screen.dart';

/// Technician app: today's jobs in order, the daily cash closing, account.
class TechHome extends StatefulWidget {
  const TechHome({super.key});

  @override
  State<TechHome> createState() => _TechHomeState();
}

class _TechHomeState extends State<TechHome> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    const titles = ['شغلي', 'تقفيل اليوم', 'حسابي'];
    return Scaffold(
      appBar: AppBar(
        title: Text(titles[_tab]),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: IndexedStack(
          index: _tab,
          children: [
            const JobsList(),
            const ClosingScreen(),
            ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.engineering)),
                    title: Text(
                      '${s.user?['full_name'] ?? ''}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    subtitle: Text(
                      '${s.user?['phone'] ?? ''}',
                      textDirection: TextDirection.ltr,
                      textAlign: TextAlign.right,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: s.logout,
                  icon: const Icon(Icons.logout),
                  label: const Text('تسجيل خروج'),
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
          NavigationDestination(
            icon: Icon(Icons.format_list_numbered),
            label: 'شغلي',
          ),
          NavigationDestination(
            icon: Icon(Icons.payments_outlined),
            label: 'التقفيل',
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

class JobsList extends StatefulWidget {
  const JobsList({super.key});

  @override
  State<JobsList> createState() => _JobsListState();
}

class _JobsListState extends State<JobsList> {
  DateTime _day = DateTime.now();
  List<dynamic>? _jobs;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _iso =>
      '${_day.year}-${_day.month.toString().padLeft(2, '0')}-${_day.day.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('technician/jobs/', {
        'date': _iso,
      });
      setState(() => (_jobs = r as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  void _shift(int days) {
    setState(() => (_day = _day.add(Duration(days: days)), _jobs = null));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 8, 0),
          child: Row(
            children: [
              IconButton(
                onPressed: () => _shift(-1),
                icon: const Icon(Icons.chevron_right),
              ),
              Expanded(
                child: Text(
                  '${dayLabel(_day)} ${shortDate(_day)}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              IconButton(
                onPressed: () => _shift(1),
                icon: const Icon(Icons.chevron_left),
              ),
            ],
          ),
        ),
        Expanded(
          child: _error != null
              ? ErrorRetry(error: _error!, onRetry: _load)
              : _jobs == null
              ? const Loading()
              : _jobs!.isEmpty
              ? const EmptyState(
                  icon: Icons.free_breakfast_outlined,
                  text: 'مفيش شغل اليوم ده.',
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _jobs!.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (_, i) => _jobCard(i + 1, _jobs![i]),
                  ),
                ),
        ),
      ],
    );
  }

  Widget _jobCard(int n, Map j) {
    final start = parseServerTime('${j['scheduled_start']}');
    final end = parseServerTime('${j['scheduled_end']}');
    final a = j['address_details'] as Map;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => JobDetailScreen(orderId: j['id'] as int),
            ),
          );
          _load();
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                backgroundColor: BrandColors.layl,
                foregroundColor: Colors.white,
                child: Text('$n'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${clock(start)} - ${clock(end)}',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        statusPill(j),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('${j['customer_name']} • ${j['zone_name']}'),
                    Muted(
                      [
                        a['street'],
                        'عمارة ${a['building']}',
                        a['landmark'],
                      ].where((x) => '${x ?? ''}'.isNotEmpty).join(' • '),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      (j['items'] as List)
                          .map((i) => '${i['car_name']} (${i['car_color']})')
                          .join('، '),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
