import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';
import 'today_screen.dart';

/// Close a day for one zone or all zones (bad weather). That day's bookings are
/// cancelled free and customers get a "book a new time" button.
class CloseDayScreen extends StatefulWidget {
  const CloseDayScreen({super.key});

  @override
  State<CloseDayScreen> createState() => _CloseDayScreenState();
}

class _CloseDayScreenState extends State<CloseDayScreen> {
  DateTime _day = DateTime.now();
  int? _zone; // null = all zones
  final _reason = TextEditingController();
  List<dynamic> _zones = [], _closed = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.read<Session>().api;
    final z = await api.get('zones/') as List;
    final c = await api.get('manage/closed-days/') as List;
    if (mounted) setState(() => (_zones = z, _closed = c));
  }

  Future<void> _close() async {
    final zoneName = _zone == null
        ? 'كل المناطق'
        : _zones.firstWhere((z) => z['id'] == _zone)['name'];
    final ok = await confirmDialog(
      context,
      'تقفل يوم ${isoDay(_day)}؟',
      '$zoneName. كل الحجوزات اللي مبدأتش هتتلغي ببلاش، والعملاء هيوصلهم إشعار يحجزوا تاني.',
      yes: 'اقفل',
    );
    if (!ok || !mounted) return;
    final r = await context.read<Session>().api.post('manage/closed-days/', {
      'date': isoDay(_day),
      'zone': _zone,
      'reason': _reason.text.trim(),
    });
    if (mounted) {
      showInfo(context, 'اليوم اتقفل. اتلغى ${r['cancelled_orders']} حجز.');
    }
    _reason.clear();
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('قفل يوم (الجو)')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.event),
              title: Text(isoDay(_day)),
              trailing: const Icon(Icons.edit_calendar_outlined),
              onTap: () async {
                final d = await showDatePicker(
                  context: context,
                  initialDate: _day,
                  firstDate: DateTime.now().subtract(const Duration(days: 1)),
                  lastDate: DateTime.now().add(const Duration(days: 60)),
                );
                if (d != null) setState(() => _day = d);
              },
            ),
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<int?>(
            initialValue: _zone,
            decoration: const InputDecoration(labelText: 'المنطقة'),
            items: [
              const DropdownMenuItem<int?>(
                value: null,
                child: Text('كل المناطق'),
              ),
              for (final z in _zones)
                DropdownMenuItem<int?>(
                  value: z['id'] as int,
                  child: Text('${z['name']}'),
                ),
            ],
            onChanged: (v) => setState(() => _zone = v),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _reason,
            decoration: const InputDecoration(
              labelText: 'السبب (العميل هيشوفه)',
              hintText: 'مثلاً: مطر شديد',
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 14),
          BusyButton(
            label: 'اقفل اليوم',
            icon: Icons.block,
            onPressed: _reason.text.trim().isEmpty ? null : _close,
          ),
          const SectionTitle('أيام مقفولة'),
          if (_closed.isEmpty) const Muted('مفيش.'),
          for (final c in _closed)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text('${c['date']} • ${c['zone_name']}'),
                subtitle: Text('${c['reason']}'),
                trailing: TextButton(
                  onPressed: () async {
                    await context.read<Session>().api.delete(
                      'manage/closed-days/${c['id']}/',
                    );
                    _load();
                  },
                  child: const Text('افتح تاني'),
                ),
              ),
            ),
          const Muted(
            '«افتح تاني» بيرجّع اليوم للحجز الجديد بس، والحجوزات اللي اتلغت مش بترجع.',
          ),
        ],
      ),
    );
  }
}
