import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'checkout_screen.dart';

/// Booking step 3: day and time. Only times a technician can really make are shown.
/// With rescheduleOrderId: moves an existing order instead of booking a new one.
class SlotsScreen extends StatefulWidget {
  const SlotsScreen({
    super.key,
    required this.addressId,
    required this.items,
    this.rescheduleOrderId,
    this.pickLabel,
  });
  final int addressId;
  final List<Map<String, dynamic>> items;
  final int? rescheduleOrderId;

  /// Only choose a time and return it (subscriptions); the button says this.
  final String? pickLabel;

  @override
  State<SlotsScreen> createState() => _SlotsScreenState();
}

class _SlotsScreenState extends State<SlotsScreen> {
  Map<String, dynamic>? _data;
  Object? _error;
  int _day = 0;
  String? _start;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<Session>().api.post('booking/slots/', {
        'address': widget.addressId,
        'items': widget.items,
      });
      final data = Map<String, dynamic>.from(d);
      final days = data['days'] as List;
      final firstWithSlots = days.indexWhere(
        (x) => (x['slots'] as List).isNotEmpty,
      );
      setState(() {
        _data = data;
        _error = null;
        _day = firstWithSlots < 0 ? 0 : firstWithSlots;
        _start = null;
      });
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _express() async {
    final api = context.read<Session>().api;
    final order = await api.post('orders/', {
      'address': widget.addressId,
      'items': widget.items,
      'start': '${_data!['express']['start']}',
      'express': true,
    });
    if (!mounted) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CheckoutScreen(order: Map<String, dynamic>.from(order)),
      ),
    );
    if (mounted) _load();
  }

  Future<void> _book() async {
    if (widget.pickLabel != null) {
      Navigator.pop(context, _start);
      return;
    }
    final api = context.read<Session>().api;
    if (widget.rescheduleOrderId != null) {
      await api.post('orders/${widget.rescheduleOrderId}/reschedule/', {
        'start': _start,
      });
      if (!mounted) return;
      showInfo(context, 'الميعاد اتغير.');
      Navigator.pop(context, true);
      return;
    }
    final order = await api.post('orders/', {
      'address': widget.addressId,
      'items': widget.items,
      'start': _start,
    });
    if (!mounted) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CheckoutScreen(order: Map<String, dynamic>.from(order)),
      ),
    );
    if (mounted) _load(); // if the hold expired, times may have changed
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.rescheduleOrderId != null ? 'ميعاد جديد' : 'الميعاد',
        ),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _data == null
          ? const Loading()
          : _body(),
      bottomNavigationBar: _data == null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: BusyButton(
                  label:
                      widget.pickLabel ??
                      (widget.rescheduleOrderId != null
                          ? 'غيّر الميعاد'
                          : 'احجز الميعاد'),
                  onPressed: _start == null ? null : _book,
                ),
              ),
            ),
    );
  }

  Widget _body() {
    final days = _data!['days'] as List;
    final slots = (days[_day]['slots'] as List);
    final charges = _data!['charges'] as List;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                KeyValue('المدة', duration(_data!['total_minutes'] as int)),
                KeyValue('السعر', money(_data!['total'])),
                for (final c in charges)
                  KeyValue(
                    '${c['label']} (طلب سابق)',
                    money(c['amount']),
                    color: BrandColors.danger,
                  ),
                if (((_data!['distance_fee'] ?? 0) as int) > 0)
                  KeyValue(
                    'رسوم المسافة (${_data!['distance_km']} كيلو)',
                    money(_data!['distance_fee']),
                  ),
                if (charges.isNotEmpty ||
                    ((_data!['distance_fee'] ?? 0) as int) > 0)
                  KeyValue('المطلوب', money(_data!['amount_due']), bold: true),
              ],
            ),
          ),
        ),
        if (charges.isNotEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Muted(
              'عليك رسوم من طلب قبل كده، وهتتضاف على الطلب ده في سطر لوحدها.',
            ),
          ),
        if (_data!['express'] != null &&
            widget.pickLabel == null &&
            widget.rescheduleOrderId == null) ...[
          const SizedBox(height: 10),
          Card(
            color: BrandColors.razaz,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'عايز حد دلوقتي؟ فني يقدر يبدأ الساعة ${clock(parseServerTime('${_data!['express']['start']}'))}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  Muted(
                    'طلب سريع، عليه رسوم ${money(_data!['express']['fee'])}.',
                  ),
                  const SizedBox(height: 8),
                  BusyButton(
                    label: 'اطلب سريع',
                    icon: Icons.bolt,
                    onPressed: _express,
                  ),
                ],
              ),
            ),
          ),
        ],
        const SectionTitle('اليوم'),
        SizedBox(
          height: 74,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: days.length,
            separatorBuilder: (_, _) => const SizedBox(width: 8),
            itemBuilder: (_, i) {
              final d = DateTime.parse('${days[i]['date']}');
              final has = (days[i]['slots'] as List).isNotEmpty;
              final on = i == _day;
              return InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: () => setState(() => (_day = i, _start = null)),
                child: Container(
                  width: 72,
                  decoration: BoxDecoration(
                    color: on ? BrandColors.layl : Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: on ? BrandColors.layl : BrandColors.line,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        dayLabel(d),
                        style: TextStyle(
                          fontSize: 12,
                          color: on ? Colors.white : BrandColors.muted,
                        ),
                      ),
                      Text(
                        '${d.day}/${d.month}',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          color: on
                              ? Colors.white
                              : (has ? BrandColors.layl : BrandColors.line),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        const SectionTitle('الساعة'),
        if (slots.isEmpty)
          const EmptyState(
            icon: Icons.event_busy_outlined,
            text: 'مفيش مواعيد فاضية اليوم ده. جرب يوم تاني.',
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final s in slots)
                ChoiceChip(
                  label: Text(clock(parseServerTime('${s['start']}'))),
                  selected: _start == s['start'],
                  onSelected: (_) => setState(() => _start = '${s['start']}'),
                ),
            ],
          ),
        const SizedBox(height: 8),
        Muted(
          'الشغل هياخد حوالي ${duration(_data!['total_minutes'] as int)}، فالمواعيد اللي مش هتلحق مش ظاهرة.',
        ),
      ],
    );
  }
}
