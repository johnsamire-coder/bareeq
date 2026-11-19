import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'detailed_reports_screen.dart';
import 'cars_catalog_screen.dart';
import 'today_screen.dart';

/// Money and work reports for a period.
class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  int _period = 2; // 0 today, 1 last 7 days, 2 this month, 3 last month
  Map<String, dynamic>? _r;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  (DateTime, DateTime) get _range {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    switch (_period) {
      case 0:
        return (today, today);
      case 1:
        return (today.subtract(const Duration(days: 6)), today);
      case 3:
        final firstThis = DateTime(now.year, now.month, 1);
        final lastPrev = firstThis.subtract(const Duration(days: 1));
        return (DateTime(lastPrev.year, lastPrev.month, 1), lastPrev);
      default:
        return (DateTime(now.year, now.month, 1), today);
    }
  }

  Future<void> _load() async {
    setState(() => _r = null);
    final (a, b) = _range;
    try {
      final r = await context.read<Session>().api.get('manage/reports/', {
        'from': isoDay(a),
        'to': isoDay(b),
      });
      setState(() => (_r = Map<String, dynamic>.from(r), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    const labels = ['النهارده', 'آخر 7 أيام', 'الشهر ده', 'الشهر اللي فات'];
    return Scaffold(
      appBar: AppBar(
        title: const Text('التقارير'),
        actions: [
          IconButton(
            tooltip: 'تقارير تفصيلية',
            icon: const Icon(Icons.groups_outlined),
            onPressed: () {
              final (a, b) = _range;
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) =>
                      DetailedReportsScreen(from: isoDay(a), to: isoDay(b)),
                ),
              );
            },
          ),
          IconButton(
            tooltip: 'صدّر Excel',
            icon: const Icon(Icons.file_download_outlined),
            onPressed: () {
              final (a, b) = _range;
              exportReport(context, isoDay(a), isoDay(b));
            },
          ),
        ],
      ),
      body: Column(
        children: [
          SizedBox(
            height: 52,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: [
                for (var i = 0; i < labels.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: ChoiceChip(
                      label: Text(labels[i]),
                      selected: _period == i,
                      onSelected: (_) {
                        _period = i;
                        _load();
                      },
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: _error != null
                ? ErrorRetry(error: _error!, onRetry: _load)
                : _r == null
                ? const Loading()
                : RefreshIndicator(onRefresh: _load, child: _body()),
          ),
        ],
      ),
    );
  }

  Widget _tile(String label, String value, {Color? color}) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: BrandColors.line),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Muted(label, size: 12),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w800,
            color: color,
          ),
        ),
      ],
    ),
  );

  Widget _bars(
    List rows, {
    String key = 'revenue',
    String Function(Map)? title,
  }) {
    final max = rows.fold<int>(
      1,
      (m, r) => (r[key] as int) > m ? r[key] as int : m,
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            if (rows.isEmpty) const Muted('مفيش بيانات.'),
            for (final r in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    SizedBox(
                      width: 110,
                      child: Text(
                        title?.call(r) ?? '${r['name']}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Expanded(
                      child: LayoutBuilder(
                        builder: (_, c) => Align(
                          alignment: AlignmentDirectional.centerStart,
                          child: Container(
                            height: 14,
                            width: c.maxWidth * (r[key] as int) / max,
                            decoration: BoxDecoration(
                              color: BrandColors.mayya,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 78,
                      child: Text(
                        money(r[key]),
                        textAlign: TextAlign.left,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _body() {
    final r = _r!;
    final t = Map<String, dynamic>.from(r['totals']);
    int v(String k) => (t[k] ?? 0) as int;
    final c = r['customers'] as Map;
    final cx = r['cancellations'] as Map;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          childAspectRatio: 2.3,
          children: [
            _tile('غسلات خلصت', '${v('orders')}'),
            _tile('الإيراد', money(v('revenue'))),
            _tile('اتحصّل فعلاً', money(v('collected'))),
            _tile('من المحفظة', money(v('wallet'))),
            _tile(
              'لسه متحصّلش',
              money(v('uncollected')),
              color: v('uncollected') > 0 ? BrandColors.danger : null,
            ),
            _tile('هامش الغسلة', money(v('margin')), color: BrandColors.good),
          ],
        ),
        const SizedBox(height: 6),
        const Muted(
          'الإيراد = اللي اتحصّل + المحفظة + اللي لسه متحصّلش. هامش الغسلة = الإيراد - الزيت - الخامات (من غير أجر الفني والبنزين).',
        ),
        const SectionTitle('الإيراد كل يوم'),
        _bars([
          for (final d in r['by_day'] as List)
            {...d, 'name': shortDate(DateTime.parse('${d['date']}'))},
        ]),
        const SectionTitle('حسب المنطقة'),
        _bars(r['by_zone'] as List),
        const SectionTitle('حسب الفني'),
        _bars(r['by_technician'] as List),
        const SectionTitle('حسب الخدمة'),
        _bars(
          r['by_service'] as List,
          title: (x) => '${x['name']} (${x['count']})',
        ),
        const SectionTitle('العملاء'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                KeyValue('اتسجلوا في الفترة', '${c['signups']}'),
                KeyValue('اتخدموا', '${c['served']}'),
                KeyValue('أول مرة', '${c['first_time']}'),
                KeyValue('رجعوا تاني', '${c['returning']}', bold: true),
              ],
            ),
          ),
        ),
        const SectionTitle('المدة الحقيقية مقابل المدة المحسوبة'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                if ((r['job_times'] as List).isEmpty)
                  const Muted('لسه مفيش طلبات بخدمة واحدة خلصت في الفترة دي.'),
                for (final j in r['job_times'] as List)
                  KeyValue(
                    '${j['service']} • ${sizeLabel('${j['size']}')} (${j['count']})',
                    '${j['actual_avg']} د / ${j['planned']} د',
                    color: (j['actual_avg'] as int) > (j['planned'] as int)
                        ? BrandColors.danger
                        : BrandColors.good,
                  ),
                const Muted(
                  'بنحسبها من الطلبات اللي فيها عربية واحدة وخدمة واحدة. لو الرقم الأحمر بيتكرر، زوّد المدة.',
                ),
              ],
            ),
          ),
        ),
        const SectionTitle('الإلغاء والتقييم'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                KeyValue('لغاه العميل', '${cx['by_customer']}'),
                KeyValue('لغته الشركة', '${cx['by_company']}'),
                KeyValue('العربية مش موجودة', '${cx['car_not_found']}'),
                KeyValue(
                  'متوسط التقييم',
                  '${(r['ratings'] as Map)['average']} من 5 (${(r['ratings'] as Map)['count']} تقييم)',
                ),
              ],
            ),
          ),
        ),
        const SectionTitle('دلوقتي'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                KeyValue(
                  'رصيد في محافظ العملاء',
                  money((r['now'] as Map)['wallet_liability']),
                ),
                KeyValue(
                  'رسوم لسه محدش دفعها',
                  money((r['now'] as Map)['unpaid_fees']),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
