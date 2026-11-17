import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'slots_screen.dart';

/// Booking step 2: services for each car. The bar at the bottom always shows the
/// live total and duration, calculated by the server (bundles, replacements, whole pounds).
class ServicesScreen extends StatefulWidget {
  const ServicesScreen({super.key, required this.addressId, required this.cars});
  final int addressId;
  final List<Map<String, dynamic>> cars;

  @override
  State<ServicesScreen> createState() => _ServicesScreenState();
}

class _ServicesScreenState extends State<ServicesScreen> {
  final Map<int, Map<String, dynamic>> _catalog = {};
  final Map<int, Set<int>> _selected = {};
  final Map<int, int?> _oil = {};
  final Map<int, Map<String, dynamic>?> _quotes = {};
  late int _carId = widget.cars.first['id'];
  Object? _error;
  Timer? _debounce;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _loadCatalogs();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _loadCatalogs() async {
    try {
      for (final c in widget.cars) {
        final id = c['id'] as int;
        _catalog[id] = Map<String, dynamic>.from(await _api.get('services/catalog/', {'address': widget.addressId, 'car': id}));
        _selected.putIfAbsent(id, () => {});
      }
      setState(() => _error = null);
    } catch (e) {
      setState(() => _error = e);
    }
  }

  void _toggle(int serviceId) {
    final sel = _selected[_carId]!;
    setState(() => sel.contains(serviceId) ? sel.remove(serviceId) : sel.add(serviceId));
    _requote();
  }

  void _applyBundle(Map b) {
    setState(() => _selected[_carId]!.addAll((b['services'] as List).cast<int>()));
    _requote();
  }

  void _requote() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), _quoteCurrent);
  }

  Future<void> _quoteCurrent() async {
    final carId = _carId;
    final sel = _selected[carId]!;
    if (sel.isEmpty) {
      setState(() => _quotes[carId] = null);
      return;
    }
    try {
      final q = Map<String, dynamic>.from(await _api.post('services/quote/', {
        'address': widget.addressId, 'car': carId, 'services': sel.toList(),
        if (_oil[carId] != null) 'oil_type': _oil[carId],
      }));
      // The server removed replaced services (e.g. detailing includes the wash).
      final removed = (q['removed_services'] as List).cast<int>();
      setState(() {
        sel.removeAll(removed);
        _quotes[carId] = q;
      });
      for (final m in q['messages'] as List) {
        if (mounted) showInfo(context, '$m');
      }
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  int get _total => _quotes.values.fold(0, (s, q) => s + ((q?['total'] ?? 0) as int));
  int get _minutes => _quotes.values.fold(0, (s, q) => s + ((q?['total_minutes'] ?? 0) as int));
  bool get _ready => widget.cars.every((c) => _selected[c['id']]?.isNotEmpty == true && _quotes[c['id']] != null);

  @override
  Widget build(BuildContext context) {
    final cat = _catalog[_carId];
    final quote = _quotes[_carId];
    return Scaffold(
      appBar: AppBar(title: const Text('الخدمات')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _loadCatalogs)
          : cat == null
              ? const Loading()
              : ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 120), children: [
                  if (widget.cars.length > 1)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Wrap(spacing: 8, children: [
                        for (final c in widget.cars)
                          ChoiceChip(
                            label: Text('${c['display_name']}'),
                            selected: _carId == c['id'],
                            onSelected: (_) => setState(() => _carId = c['id']),
                          ),
                      ]),
                    ),
                  if ((cat['bundles'] as List).isNotEmpty) ...[
                    const SectionTitle('الباقات'),
                    for (final b in cat['bundles'] as List)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Card(
                          child: ListTile(
                            title: Text('${b['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                            subtitle: Text('${b['description']}'),
                            trailing: Pill('خصم ${b['discount_percent']}%', color: const Color(0xFFFFF3D6), textColor: const Color(0xFF8A5A00)),
                            onTap: () => _applyBundle(b),
                          ),
                        ),
                      ),
                  ],
                  for (final group in _groups(cat['services'] as List)) ...[
                    SectionTitle(group.key),
                    for (final s in group.value) _serviceTile(s, cat),
                  ],
                  if (quote != null && (quote['warnings'] as List).isNotEmpty)
                    for (final w in quote['warnings'] as List)
                      Card(
                        color: const Color(0xFFFFF7E6),
                        child: ListTile(leading: const Icon(Icons.wb_sunny_outlined, color: Color(0xFF8A5A00)), title: Text('$w')),
                      ),
                  if (quote != null && quote['needs_oil_choice'] == true && (cat['oil_types'] as List).isNotEmpty) ...[
                    const SectionTitle('نوع الزيت'),
                    RadioGroup<int>(
                      groupValue: _oil[_carId],
                      onChanged: (v) {
                        setState(() => _oil[_carId] = v);
                        _requote();
                      },
                      child: Column(children: [
                        for (final o in cat['oil_types'] as List)
                          RadioListTile<int>(value: o['id'], title: Text('${o['name']}'), subtitle: Text(money(o['price']))),
                      ]),
                    ),
                  ],
                ]),
      bottomSheet: _bar(),
    );
  }

  List<MapEntry<String, List<dynamic>>> _groups(List services) {
    final map = <String, List<dynamic>>{};
    for (final s in services) {
      map.putIfAbsent('${s['category_label']}', () => []).add(s);
    }
    return map.entries.toList();
  }

  Widget _serviceTile(Map s, Map cat) {
    final on = _selected[_carId]!.contains(s['id']);
    final replaces = [
      for (final other in cat['services'] as List)
        if ((s['replaces'] as List).contains(other['id'])) other['name']
    ];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Card(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: on ? BrandColors.mayya : BrandColors.line, width: on ? 2 : 1),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _toggle(s['id']),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              ServiceIcon('${s['code']}'),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${s['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                  Muted('${s['description']}'),
                  if (replaces.isNotEmpty)
                    Padding(padding: const EdgeInsets.only(top: 4), child: Pill('بتشمل ${replaces.join('، ')}')),
                ]),
              ),
              const SizedBox(width: 8),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(money(s['price']), style: const TextStyle(fontWeight: FontWeight.w700)),
                Muted(duration(s['minutes'] as int), size: 12),
                Icon(on ? Icons.check_circle_rounded : Icons.radio_button_unchecked, color: on ? BrandColors.mayya : BrandColors.line),
              ]),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _bar() {
    final discount = _quotes.values.fold<int>(0, (s, q) => s + ((q?['discount'] ?? 0) as int));
    return Container(
      decoration: const BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: BrandColors.line))),
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
      child: SafeArea(
        top: false,
        child: Row(children: [
          Expanded(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(money(_total), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
              Muted(_minutes == 0
                  ? 'اختار خدمة'
                  : 'حوالي ${duration(_minutes)}${discount > 0 ? ' • وفّرت ${money(discount)}' : ''}'),
            ]),
          ),
          SizedBox(
            width: 150,
            child: FilledButton(
              onPressed: _ready
                  ? () => Navigator.push(context, MaterialPageRoute(
                        builder: (_) => SlotsScreen(addressId: widget.addressId, items: [
                          for (final c in widget.cars)
                            {
                              'car': c['id'],
                              'services': _selected[c['id']]!.toList(),
                              if (_oil[c['id']] != null) 'oil_type': _oil[c['id']],
                            }
                        ]),
                      ))
                  : null,
              child: const Text('اختار الميعاد'),
            ),
          ),
        ]),
      ),
    );
  }
}
