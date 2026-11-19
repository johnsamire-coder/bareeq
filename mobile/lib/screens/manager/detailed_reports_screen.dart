import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// Opens an Excel file of a report (a short-lived link the phone downloads).
Future<void> exportReport(
  BuildContext context,
  String from,
  String to, {
  String? only,
}) async {
  const kinds = {
    'summary': 'الملخص والأيام والخدمات',
    'technicians': 'الفنيين',
    'zones': 'المناطق',
    'retention': 'العملاء (رجعوا وبطّلوا)',
  };
  final kind =
      only ??
      await showModalBottomSheet<String>(
        context: context,
        builder: (c) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: [
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'صدّر ملف Excel',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ),
              for (final e in kinds.entries)
                ListTile(
                  leading: const Icon(Icons.table_view),
                  title: Text(e.value),
                  onTap: () => Navigator.pop(c, e.key),
                ),
            ],
          ),
        ),
      );
  if (kind == null || !context.mounted) return;
  final r = await context.read<Session>().api.post('manage/reports/export/', {
    'report': kind,
    'from': from,
    'to': to,
  });
  await launchUrl(
    Uri.parse('${r['url']}'),
    mode: LaunchMode.externalApplication,
  );
}

/// Per technician, per zone, and customers coming back or lost.
class DetailedReportsScreen extends StatelessWidget {
  const DetailedReportsScreen({
    super.key,
    required this.from,
    required this.to,
  });
  final String from, to;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('تقارير تفصيلية'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'الفنيين'),
              Tab(text: 'المناطق'),
              Tab(text: 'العملاء'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _Report(
              path: 'manage/reports/technicians/',
              from: from,
              to: to,
              kind: 'technicians',
              build: _technicians,
            ),
            _Report(
              path: 'manage/reports/zones/',
              from: from,
              to: to,
              kind: 'zones',
              build: _zones,
            ),
            _Report(
              path: 'manage/reports/retention/',
              from: from,
              to: to,
              kind: 'retention',
              build: _retention,
            ),
          ],
        ),
      ),
    );
  }

  static List<Widget> _technicians(Map r) => [
    for (final t in r['rows'] as List)
      Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              KeyValue('${t['name']}', money(t['revenue']), bold: true),
              KeyValue('طلبات خلصت', '${t['completed']}'),
              KeyValue(
                'في ميعاده',
                t['on_time_percent'] == null ? '-' : '${t['on_time_percent']}%',
              ),
              KeyValue(
                'الوقت الفعلي / المتوقع',
                t['avg_actual_minutes'] == null
                    ? '-'
                    : '${t['avg_actual_minutes']} / ${t['avg_planned_minutes']} دقيقة',
              ),
              KeyValue(
                'التقييم',
                '${t['rating_avg']} (${t['ratings']}) • وحشة ${t['bad_ratings']}',
              ),
              KeyValue('العربية مش موجودة', '${t['car_not_found']}'),
              KeyValue('طلبات سريعة', '${t['express']}'),
              KeyValue('الخامات', money(t['materials_cost'])),
              KeyValue(
                'العهدة',
                money(t['custody_balance']),
                color: (t['custody_balance'] as int) > 0
                    ? BrandColors.danger
                    : null,
              ),
            ],
          ),
        ),
      ),
  ];

  static List<Widget> _zones(Map r) => [
    if ((r['rows'] as List).isEmpty)
      const Muted('مفيش طلبات خلصت في الفترة دي.'),
    for (final z in r['rows'] as List)
      Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              KeyValue('${z['name']}', money(z['revenue']), bold: true),
              KeyValue('الطلبات', '${z['orders']}'),
              KeyValue('عملاء جداد', '${z['new_customers']}'),
              KeyValue('طلبات سريعة', '${z['express']}'),
              KeyValue('رسوم المسافة', money(z['distance_fees'])),
              KeyValue('التقييم', '${z['rating_avg']}'),
            ],
          ),
        ),
      ),
  ];

  static List<Widget> _retention(Map r) => [
    Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            KeyValue('اتخدموا في الفترة', '${r['served']}', bold: true),
            KeyValue('أول مرة', '${r['first_time']}'),
            KeyValue('رجعوا تاني', '${r['returning']}'),
            const Divider(color: BrandColors.line),
            KeyValue('كل العملاء اللي طلبوا', '${r['customers_ever']}'),
            KeyValue('طلبوا مرتين أو أكتر', '${r['came_twice_or_more']}'),
            KeyValue(
              'بطّلوا (مفيش طلب من ${r['lost_after_days']} يوم)',
              '${r['lost']}',
              color: BrandColors.danger,
            ),
            KeyValue('مشتركين دلوقتي', '${r['active_subscriptions']}'),
          ],
        ),
      ),
    ),
    const SectionTitle('اللي بطّلوا'),
    for (final c in r['lost_customers'] as List)
      ListTile(
        dense: true,
        title: Text('${c['name']}'),
        subtitle: Text(
          '‎${c['phone']} • ${c['orders']} طلب • آخر طلب ${'${c['last_order']}'.substring(0, 10)}',
        ),
      ),
  ];
}

class _Report extends StatefulWidget {
  const _Report({
    required this.path,
    required this.from,
    required this.to,
    required this.kind,
    required this.build,
  });
  final String path, from, to, kind;
  final List<Widget> Function(Map) build;

  @override
  State<_Report> createState() => _ReportState();
}

class _ReportState extends State<_Report> {
  Map<String, dynamic>? _r;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get(widget.path, {
        'from': widget.from,
        'to': widget.to,
      });
      setState(() => (_r = Map<String, dynamic>.from(r), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) return ErrorRetry(error: _error!, onRetry: _load);
    if (_r == null) return const Loading();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Muted('من ${widget.from} لحد ${widget.to}'),
          const SizedBox(height: 8),
          ...widget.build(_r!),
          const SizedBox(height: 8),
          BusyButton(
            label: 'صدّر Excel',
            icon: Icons.file_download_outlined,
            outlined: true,
            onPressed: () => exportReport(
              context,
              widget.from,
              widget.to,
              only: widget.kind,
            ),
          ),
        ],
      ),
    );
  }
}
