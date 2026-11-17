import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

const sizes = [
  ('hatchback', 'هاتشباك'),
  ('sedan', 'سيدان'),
  ('suv', 'SUV'),
  ('luxury', 'فاخرة'),
];

Future<int?> askPounds(BuildContext context, String title, int piastres) async {
  final c = TextEditingController(
    text: piastres % 100 == 0
        ? '${piastres ~/ 100}'
        : (piastres / 100).toStringAsFixed(2),
  );
  final r = await showDialog<String>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: c,
        autofocus: true,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        textAlign: TextAlign.center,
        decoration: const InputDecoration(suffixText: 'ج.م'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(d),
          child: const Text('رجوع'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(d, c.text.trim()),
          child: const Text('احفظ'),
        ),
      ],
    ),
  );
  if (r == null) return null;
  final p = double.tryParse(r);
  if (p == null || p < 0) throw ApiError('bad', 'اكتب السعر بالجنيه.');
  return (p * 100).round();
}

/// Price of each service for a zone and a car size (pounds).
class PricesScreen extends StatefulWidget {
  const PricesScreen({super.key});

  @override
  State<PricesScreen> createState() => _PricesScreenState();
}

class _PricesScreenState extends State<PricesScreen> {
  List<dynamic> _zones = [], _services = [], _prices = [];
  int? _zone;
  String _size = 'sedan';
  bool _loading = true;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _zones = await _api.get('zones/') as List;
    _services = await _api.get('manage/services/') as List;
    _zone = _zones.isEmpty ? null : _zones.first['id'] as int;
    await _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    _prices = _zone == null
        ? []
        : await _api.get('manage/service-prices/', {
                'zone': _zone,
                'size_class': _size,
              })
              as List;
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _edit(Map service, Map? price) async {
    final v = await askPounds(
      context,
      '${service['name']}',
      (price?['price'] ?? 0) as int,
    );
    if (v == null) return;
    try {
      if (price == null) {
        await _api.post('manage/service-prices/', {
          'service': service['id'],
          'zone': _zone,
          'size_class': _size,
          'price': v,
        });
      } else {
        await _api.patch('manage/service-prices/${price['id']}/', {'price': v});
      }
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _confirmAll() async {
    if (!await confirmDialog(
      context,
      'تأكيد كل الأسعار؟',
      'كل الأسعار المؤقتة في كل المناطق والأحجام هتبقى أسعار حقيقية.',
    )) {
      return;
    }
    final r = await _api.post('manage/service-prices/confirm-all/');
    if (mounted) showInfo(context, 'اتأكد ${r['confirmed']} سعر.');
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final provisional = _prices
        .where((p) => p['is_provisional'] == true)
        .length;
    return Scaffold(
      appBar: AppBar(title: const Text('الأسعار')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<int>(
            initialValue: _zone,
            decoration: const InputDecoration(labelText: 'المنطقة'),
            items: [
              for (final z in _zones)
                DropdownMenuItem(
                  value: z['id'] as int,
                  child: Text('${z['name']}'),
                ),
            ],
            onChanged: (v) {
              _zone = v;
              _load();
            },
          ),
          const SizedBox(height: 10),
          SegmentedButton<String>(
            showSelectedIcon: false,
            segments: [
              for (final s in sizes)
                ButtonSegment(value: s.$1, label: Text(s.$2)),
            ],
            selected: {_size},
            onSelectionChanged: (v) {
              _size = v.first;
              _load();
            },
          ),
          if (provisional > 0) ...[
            const SizedBox(height: 10),
            Card(
              color: const Color(0xFFFFF7E6),
              child: ListTile(
                leading: const Icon(
                  Icons.info_outline,
                  color: Color(0xFF8A5A00),
                ),
                title: Text('$provisional سعر هنا لسه مؤقت'),
                subtitle: const Text('أي سعر تعدله بيبقى حقيقي.'),
                trailing: TextButton(
                  onPressed: _confirmAll,
                  child: const Text('أكّد الكل'),
                ),
              ),
            ),
          ],
          const SizedBox(height: 10),
          if (_loading) const Loading(),
          if (!_loading)
            for (final s in _services)
              Builder(
                builder: (_) {
                  Map? price;
                  for (final p in _prices) {
                    if (p['service'] == s['id']) price = p;
                  }
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: ServiceIcon('${s['code']}', size: 30),
                      title: Text(
                        '${s['name']}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: price?['is_provisional'] == true
                          ? const Text(
                              'مؤقت',
                              style: TextStyle(color: Color(0xFF8A5A00)),
                            )
                          : null,
                      trailing: Text(
                        price == null ? 'مش متسعّر' : money(price['price']),
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          color: price == null ? BrandColors.danger : null,
                        ),
                      ),
                      onTap: () => _edit(s, price),
                    ),
                  );
                },
              ),
          const Muted(
            'الخدمة اللي ملهاش سعر في منطقة وحجم معينين مبتظهرش للعميل هناك.',
          ),
        ],
      ),
    );
  }
}

/// Minutes of each service for each car size.
class DurationsScreen extends StatefulWidget {
  const DurationsScreen({super.key});

  @override
  State<DurationsScreen> createState() => _DurationsScreenState();
}

class _DurationsScreenState extends State<DurationsScreen> {
  List<dynamic> _services = [], _rows = [];
  String _size = 'sedan';

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    _services = await _api.get('manage/services/') as List;
    final all = await _api.get('manage/service-durations/') as List;
    if (mounted) {
      setState(
        () => _rows = all.where((r) => r['size_class'] == _size).toList(),
      );
    }
  }

  Future<void> _edit(Map s, Map? row) async {
    final c = TextEditingController(text: '${row?['minutes'] ?? ''}');
    final v = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('${s['name']}'),
        content: TextField(
          controller: c,
          autofocus: true,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          decoration: const InputDecoration(suffixText: 'دقيقة'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d),
            child: const Text('رجوع'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(d, c.text.trim()),
            child: const Text('احفظ'),
          ),
        ],
      ),
    );
    final m = int.tryParse(v ?? '');
    if (m == null) return;
    try {
      if (row == null) {
        await _api.post('manage/service-durations/', {
          'service': s['id'],
          'size_class': _size,
          'minutes': m,
        });
      } else {
        await _api.patch('manage/service-durations/${row['id']}/', {
          'minutes': m,
        });
      }
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('المدد')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SegmentedButton<String>(
            showSelectedIcon: false,
            segments: [
              for (final s in sizes)
                ButtonSegment(value: s.$1, label: Text(s.$2)),
            ],
            selected: {_size},
            onSelectionChanged: (v) {
              _size = v.first;
              _load();
            },
          ),
          const SizedBox(height: 12),
          for (final s in _services)
            Builder(
              builder: (_) {
                Map? row;
                for (final r in _rows) {
                  if (r['service'] == s['id']) row = r;
                }
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: ServiceIcon('${s['code']}', size: 30),
                    title: Text('${s['name']}'),
                    trailing: Text(
                      row == null ? '—' : duration(row['minutes'] as int),
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    onTap: () => _edit(s, row),
                  ),
                );
              },
            ),
          const Muted(
            'المدد دي بتتحسب منها المواعيد. متوسط المدة الحقيقية لكل خدمة في «التقارير».',
          ),
        ],
      ),
    );
  }
}
