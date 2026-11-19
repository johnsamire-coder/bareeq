import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../subscriptions/subscriptions_screen.dart' show weekdays;
import 'crud.dart';
import 'lists.dart';

/// Subscription plans (the manager makes them; stop a plan instead of deleting).
Widget subscriptionPlansScreen() => CrudScreen(
  title: 'باقات الاشتراك',
  endpoint: 'manage/subscription-plans/',
  note:
      'السعر بيتحسب لكل عميل من جدول الأسعار (المنطقة وحجم العربية) × عدد الغسلات − الخصم. '
      'ومينفعش يبقى فيها تغيير زيت.',
  itemTitle: (r) => '${r['name']}',
  itemSubtitle: (r) =>
      '${r['washes_per_month']} غسلات في الشهر • خصم ${r['discount_percent']}%'
      '${r['is_active'] == true ? '' : ' • متوقفة'}',
  newDefaults: const {
    'is_active': true,
    'services': [],
    'washes_per_month': 4,
    'discount_percent': 15,
  },
  fields: [
    const FieldSpec('name', 'اسم الباقة', FieldType.text, required: true),
    const FieldSpec(
      'washes_per_month',
      'عدد الغسلات في الشهر',
      FieldType.integer,
      required: true,
    ),
    FieldSpec(
      'services',
      'الخدمات في كل غسلة',
      FieldType.multi,
      options: serviceOptions,
    ),
    const FieldSpec(
      'discount_percent',
      'الخصم عن السعر العادي %',
      FieldType.integer,
      required: true,
    ),
    const FieldSpec('sort_order', 'الترتيب', FieldType.integer),
    const FieldSpec('is_active', 'متاحة للعملاء', FieldType.boolean),
  ],
);

/// Subscribers and the month's subscription money.
class SubscriptionsAdminScreen extends StatefulWidget {
  const SubscriptionsAdminScreen({super.key});

  @override
  State<SubscriptionsAdminScreen> createState() =>
      _SubscriptionsAdminScreenState();
}

class _SubscriptionsAdminScreenState extends State<SubscriptionsAdminScreen> {
  List<dynamic>? _subs;
  Map<String, dynamic>? _rep;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<Session>().api;
      final subs = await api.get('manage/subscriptions/', {'status': 'active'});
      final rep = await api.get('manage/reports/subscriptions/');
      setState(
        () => (
          _subs = subs as List,
          _rep = Map<String, dynamic>.from(rep),
          _error = null,
        ),
      );
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الاشتراكات')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _subs == null
          ? const Loading()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    color: BrandColors.razaz,
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        children: [
                          KeyValue(
                            'مشتركين دلوقتي',
                            '${_rep!['active_subscriptions']}',
                            bold: true,
                          ),
                          KeyValue(
                            'موقفين التجديد',
                            '${_rep!['renewals_off']}',
                          ),
                          const Divider(color: BrandColors.line),
                          KeyValue('شهر ${_rep!['month']}', ''),
                          KeyValue(
                            'شهور اتدفعت',
                            '${_rep!['months_paid']} (جداد ${_rep!['new']} • تجديد ${_rep!['renewed']})',
                          ),
                          KeyValue(
                            'إيراد الاشتراكات',
                            money(_rep!['revenue']),
                            bold: true,
                          ),
                          KeyValue(
                            'الخصم اللي اتدى',
                            money(_rep!['discount_given']),
                          ),
                          KeyValue(
                            'اتدفع من المحفظة',
                            money(_rep!['from_wallet']),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SectionTitle('المشتركين'),
                  if (_subs!.isEmpty) const Muted('مفيش مشتركين لسه.'),
                  for (final s in _subs!) _row(s as Map),
                ],
              ),
            ),
    );
  }

  Widget _row(Map s) {
    final p = s['current'] as Map?;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            KeyValue(
              '${s['customer_name']}',
              '\u200E${s['customer_phone']}',
              bold: true,
            ),
            Muted(
              '${s['plan_name']} • ${s['car_name']} • كل ${weekdays[s['weekday'] as int]} '
              '${'${s['start_time']}'.substring(0, 5)} • ${s['technician_name'] ?? '-'}',
            ),
            if (p != null)
              KeyValue(
                'الشهر ${p['number']} لحد ${p['end_date']}',
                '${p['status_label']}${s['renew'] == true ? '' : ' • مش هيجدد'}',
              ),
          ],
        ),
      ),
    );
  }
}
