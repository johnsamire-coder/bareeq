import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../booking/slots_screen.dart';
import '../orders/order_detail_screen.dart';
import '../orders/status.dart';
import 'period_pay_screen.dart';
import 'subscribe_screen.dart';

const weekdays = [
  'الاتنين',
  'التلات',
  'الأربع',
  'الخميس',
  'الجمعة',
  'السبت',
  'الحد',
];

/// «اشتراكي الشهري»: the customer's subscriptions, the month's visits,
/// paying, renewing and booking a visit the company cancelled.
class SubscriptionsScreen extends StatefulWidget {
  const SubscriptionsScreen({super.key});

  @override
  State<SubscriptionsScreen> createState() => _SubscriptionsScreenState();
}

class _SubscriptionsScreenState extends State<SubscriptionsScreen> {
  List<dynamic>? _subs;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('my-subscriptions/');
      setState(() => (_subs = r as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _go(Widget page) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => page));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('اشتراكي الشهري')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _go(const SubscribeScreen()),
        icon: const Icon(Icons.add),
        label: const Text('اشترك'),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _subs == null
          ? const Loading()
          : _subs!.isEmpty
          ? const EmptyState(
              icon: Icons.event_repeat,
              text:
                  'مفيش اشتراك لسه. اشترك في باقة شهرية وخد خصم، وميعادك ثابت كل أسبوع.',
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
                children: [for (final s in _subs!) _sub(s as Map)],
              ),
            ),
    );
  }

  Widget _sub(Map s) {
    final api = context.read<Session>().api;
    final p = s['current'] as Map?;
    final time = '${s['start_time']}'.substring(0, 5);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${s['plan_name']}',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
            ),
            Muted(
              '${s['car_name']} • كل ${weekdays[s['weekday'] as int]} الساعة $time'
              '${s['technician_name'] != null ? ' • ${s['technician_name']}' : ''}',
            ),
            if (p != null) ...[
              const Divider(color: BrandColors.line),
              KeyValue(
                'الشهر ${p['number']}',
                '${p['start_date']} ← ${p['end_date']}',
              ),
              KeyValue('السعر', money(p['price']), bold: true),
              KeyValue('الحالة', '${p['status_label']}'),
              for (final v in p['visits'] as List)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  title: Text(
                    fullWhen(parseServerTime('${v['scheduled_start']}')),
                  ),
                  trailing: statusPill(v as Map),
                  onTap: () => _go(OrderDetailScreen(orderId: v['id'] as int)),
                ),
              if (p['status'] == 'pending_payment')
                BusyButton(
                  label: 'ادفع الشهر (${money(p['price'])})',
                  onPressed: () async => _go(
                    PeriodPayScreen(period: Map<String, dynamic>.from(p)),
                  ),
                ),
              if (((p['makeup_visits'] ?? 0) as int) > 0) ...[
                const SizedBox(height: 8),
                BusyButton(
                  label: 'احجز الزيارة اللي اتلغت (${p['makeup_visits']})',
                  outlined: true,
                  onPressed: () async {
                    final start = await Navigator.push<String>(
                      context,
                      MaterialPageRoute(
                        builder: (_) => SlotsScreen(
                          addressId: s['address'] as int,
                          items: [
                            {'car': s['car'], 'services': s['service_ids']},
                          ],
                          pickLabel: 'احجز الزيارة',
                        ),
                      ),
                    );
                    if (start == null) return;
                    await api.post('subscription-periods/${p['id']}/makeup/', {
                      'start': start,
                    });
                    if (mounted) showInfo(context, 'الزيارة اتحجزت.');
                    _load();
                  },
                ),
              ],
            ],
            if (s['status'] == 'active' && p?['status'] == 'paid') ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: BusyButton(
                      label: 'جدد الشهر الجاي',
                      onPressed: () async {
                        await api.post('my-subscriptions/${s['id']}/renew/');
                        _load();
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (s['renew'] == true)
                    Expanded(
                      child: BusyButton(
                        label: 'وقف التجديد',
                        outlined: true,
                        onPressed: () async {
                          final ok = await confirmDialog(
                            context,
                            'توقف التجديد؟',
                            'الشهر اللي دفعته هيكمل عادي، ومش هيجيلك تذكير تجدد.',
                          );
                          if (!ok) return;
                          await api.post(
                            'my-subscriptions/${s['id']}/stop-renewal/',
                          );
                          _load();
                        },
                      ),
                    ),
                ],
              ),
            ],
            if (s['status'] == 'ended') const Muted('الاشتراك ده خلص.'),
          ],
        ),
      ),
    );
  }
}
