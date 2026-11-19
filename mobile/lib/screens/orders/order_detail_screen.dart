import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/photo_grid.dart';
import '../booking/checkout_screen.dart';
import '../booking/slots_screen.dart';
import 'damage_report_screen.dart';
import 'rating_screen.dart';
import 'status.dart';

class OrderDetailScreen extends StatefulWidget {
  const OrderDetailScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends State<OrderDetailScreen> {
  Map<String, dynamic>? _o;
  Map<String, dynamic>? _invoice;
  List<dynamic> _photos = [];
  Object? _error;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = Map<String, dynamic>.from(
        await _api.get('orders/${widget.orderId}/'),
      );
      Map<String, dynamic>? inv;
      List<dynamic> photos = [];
      if (o['status'] == 'completed') {
        inv = Map<String, dynamic>.from(
          await _api.get('orders/${widget.orderId}/invoice/'),
        );
        photos = await _api.get('orders/${widget.orderId}/photos/') as List;
      }
      setState(() => (_o = o, _invoice = inv, _photos = photos, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _cancel() async {
    final info = await _api.get('payment-info/');
    final hours = info['cancellation_free_until_hours'];
    final fee = money(info['cancellation_late_fee']);
    if (!mounted) return;
    final ok = await confirmDialog(
      context,
      'تلغي الطلب؟',
      'الإلغاء ببلاش لحد $hours ساعة قبل الميعاد. بعد كده بيتحسب $fee على طلبك الجاي.',
      yes: 'ألغي الطلب',
      no: 'رجوع',
    );
    if (!ok) return;
    await _api.post('orders/${widget.orderId}/cancel/', {'reason': ''});
    _load();
  }

  Future<void> _reschedule() async {
    final items = [
      for (final it in _o!['items'] as List)
        {
          'car': it['car'],
          'services': [
            for (final l in it['quote']['lines'] as List) l['service'],
          ],
          if (it['quote']['oil'] != null) 'oil_type': it['quote']['oil']['id'],
        },
    ];
    final changed = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => SlotsScreen(
          addressId: _o!['address'] as int,
          items: items,
          rescheduleOrderId: widget.orderId,
        ),
      ),
    );
    if (changed == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('طلب ${widget.orderId}')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _o == null
          ? const Loading()
          : RefreshIndicator(onRefresh: _load, child: _body()),
    );
  }

  Widget _body() {
    final o = _o!;
    final status = '${o['status']}';
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        fullWhen(parseServerTime('${o['scheduled_start']}')),
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    statusPill(o),
                  ],
                ),
                const SizedBox(height: 6),
                Muted(
                  'الفني: ${o['technician_name'] ?? '-'} • ${o['zone_name']} • حوالي ${duration(o['total_minutes'] as int)}',
                ),
                if ('${o['cancel_reason'] ?? ''}'.isNotEmpty)
                  Muted('السبب: ${o['cancel_reason']}'),
              ],
            ),
          ),
        ),
        const SectionTitle('التفاصيل'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                for (final item in o['items'] as List) ...[
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: Text(
                      '${item['car_name']}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                  for (final line in item['quote']['lines'] as List)
                    KeyValue('${line['name']}', money(line['price'])),
                  if (item['quote']['oil'] != null)
                    KeyValue(
                      'زيت: ${item['quote']['oil']['name']}',
                      money(item['quote']['oil']['price']),
                    ),
                ],
                if ((o['discount'] as int) > 0)
                  KeyValue(
                    'الخصم',
                    '- ${money(o['discount'])}',
                    color: BrandColors.good,
                  ),
                if ((o['extra_discount'] as int) > 0)
                  KeyValue(
                    extraDiscountTitle(o),
                    '- ${money(o['extra_discount'])}',
                    color: BrandColors.good,
                  ),
                if ((o['charges_total'] as int) > 0)
                  KeyValue(
                    'رسوم من طلب سابق',
                    money(o['charges_total']),
                    color: BrandColors.danger,
                  ),
                const Divider(color: BrandColors.line),
                KeyValue('الإجمالي', money(o['amount_due']), bold: true),
                if ((o['wallet_used'] as int) > 0)
                  KeyValue('من المحفظة', '- ${money(o['wallet_used'])}'),
                if ({
                      'confirmed',
                      'on_the_way',
                      'arrived',
                      'in_progress',
                    }.contains(status) &&
                    (o['amount_to_collect'] as int) > 0)
                  KeyValue(
                    'هتدفع للفني كاش',
                    money(o['amount_to_collect']),
                    bold: true,
                  ),
              ],
            ),
          ),
        ),
        if (_invoice != null) ...[
          const SectionTitle('الفاتورة'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  KeyValue(
                    'رقم الفاتورة',
                    '${_invoice!['number']}',
                    bold: true,
                  ),
                  KeyValue('الإجمالي', money(_invoice!['total'])),
                  if ((_invoice!['wallet_amount'] as int) > 0)
                    KeyValue('من المحفظة', money(_invoice!['wallet_amount'])),
                  if ((_invoice!['instapay_amount'] as int) > 0)
                    KeyValue('InstaPay', money(_invoice!['instapay_amount'])),
                  if ((_invoice!['cash_amount'] as int) > 0)
                    KeyValue('كاش', money(_invoice!['cash_amount'])),
                  if (_invoice!['status'] == 'cancelled')
                    const KeyValue(
                      'الحالة',
                      'ملغية',
                      color: BrandColors.danger,
                    ),
                ],
              ),
            ),
          ),
        ],
        if (_photos.isNotEmpty) ...[
          const SectionTitle('صور قبل وبعد'),
          PhotoGrid(photos: _photos),
        ],
        const SizedBox(height: 16),
        if (status == 'pending_payment')
          FilledButton(
            onPressed: () async {
              await Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => CheckoutScreen(order: o)),
              );
              _load();
            },
            child: const Text('كمّل الدفع'),
          ),
        if (status == 'confirmed') ...[
          OutlinedButton.icon(
            onPressed: _reschedule,
            icon: const Icon(Icons.event_repeat),
            label: const Text('غيّر الميعاد'),
          ),
          const SizedBox(height: 8),
          BusyButton(
            label: 'ألغي الطلب',
            outlined: true,
            icon: Icons.close,
            onPressed: _cancel,
          ),
        ],
        if (status == 'completed') ...[
          if (o['is_rated'] != true)
            FilledButton.icon(
              onPressed: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => RatingScreen(orderId: widget.orderId),
                  ),
                );
                _load();
              },
              icon: const Icon(Icons.star_rounded),
              label: const Text('قيّم الخدمة'),
            ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => DamageReportScreen(orderId: widget.orderId),
              ),
            ),
            icon: const Icon(Icons.report_outlined),
            label: const Text('بلّغ عن ضرر'),
          ),
        ],
      ],
    );
  }
}
