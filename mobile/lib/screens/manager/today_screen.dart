import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import 'live_map_screen.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../orders/status.dart';
import 'manager_order_screen.dart';

String isoDay(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// Orders of a day grouped by technician.
class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key});

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  DateTime _day = DateTime.now();
  List<dynamic>? _orders;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('manage/orders/', {
        'date': isoDay(_day),
      });
      setState(
        () => (
          _orders = (r as List).where((o) => o['status'] != 'expired').toList(),
          _error = null,
        ),
      );
    } catch (e) {
      setState(() => _error = e);
    }
  }

  void _shift(int d) {
    setState(() => (_day = _day.add(Duration(days: d)), _orders = null));
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
              IconButton(
                tooltip: 'خريطة اليوم',
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const LiveMapScreen()),
                ),
                icon: const Icon(Icons.map_outlined),
              ),
            ],
          ),
        ),
        Expanded(
          child: _error != null
              ? ErrorRetry(error: _error!, onRetry: _load)
              : _orders == null
              ? const Loading()
              : RefreshIndicator(onRefresh: _load, child: _list()),
        ),
      ],
    );
  }

  Widget _list() {
    const live = {
      'pending_payment',
      'confirmed',
      'on_the_way',
      'arrived',
      'in_progress',
      'completed',
    };
    final active = _orders!.where((o) => live.contains(o['status'])).toList();
    final revenue = active.fold<int>(0, (s, o) => s + (o['amount_due'] as int));
    final done = _orders!.where((o) => o['status'] == 'completed').length;
    final groups = <String, List<dynamic>>{};
    for (final o in _orders!) {
      groups
          .putIfAbsent('${o['technician_name'] ?? 'من غير فني'}', () => [])
          .add(o);
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            _stat('طلبات', '${active.length}'),
            const SizedBox(width: 8),
            _stat('خلصت', '$done'),
            // A supervisor sees no money.
            if (context.read<Session>().role != 'supervisor') ...[
              const SizedBox(width: 8),
              _stat('الإيراد', money(revenue)),
            ],
          ],
        ),
        if (_orders!.isEmpty)
          const EmptyState(
            icon: Icons.event_available_outlined,
            text: 'مفيش طلبات اليوم ده.',
          ),
        for (final g in groups.entries) ...[
          SectionTitle('${g.key} (${g.value.length})'),
          for (final o in g.value)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text(
                  '${clock(parseServerTime('${o['scheduled_start']}'))} • ${o['customer_name']}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Row(
                    children: [
                      statusPill(o),
                      const SizedBox(width: 8),
                      Expanded(child: Muted('${o['zone_name']}')),
                    ],
                  ),
                ),
                trailing: Text(
                  money(o['amount_due']),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                onTap: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) =>
                          ManagerOrderScreen(orderId: o['id'] as int),
                    ),
                  );
                  _load();
                },
              ),
            ),
        ],
      ],
    );
  }

  Widget _stat(String label, String value) => Expanded(
    child: Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: BrandColors.line),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          ),
          Muted(label, size: 12),
        ],
      ),
    ),
  );
}
