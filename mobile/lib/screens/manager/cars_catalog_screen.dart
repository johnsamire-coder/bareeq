import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/session.dart';
import '../../widgets/common.dart';
import '../../widgets/search_picker.dart';
import 'pricing_screens.dart';

String sizeLabel(String s) => {for (final x in sizes) x.$1: x.$2}[s] ?? s;

/// Brands -> models with their size (the size decides price and duration).
class CarsCatalogScreen extends StatefulWidget {
  const CarsCatalogScreen({super.key});

  @override
  State<CarsCatalogScreen> createState() => _CarsCatalogScreenState();
}

class _CarsCatalogScreenState extends State<CarsCatalogScreen> {
  List<dynamic>? _brands;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final b = await context.read<Session>().api.get('car-brands/', {
      'search': _q,
    });
    if (mounted) setState(() => _brands = b as List);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الماركات والموديلات')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'دوّر على ماركة',
              ),
              onChanged: (v) {
                _q = v;
                _load();
              },
            ),
          ),
          Expanded(
            child: _brands == null
                ? const Loading()
                : ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    children: [
                      for (final b in _brands!)
                        Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            title: Text(
                              '${b['name_ar']} • ${b['name_en']}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            trailing: b['is_active'] == true
                                ? const Icon(Icons.chevron_left)
                                : const Pill('مخفية'),
                            onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => BrandModelsScreen(brand: b),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

Future<String?> pickSize(
  BuildContext context,
  String title, [
  String? current,
]) => showModalBottomSheet<String>(
  context: context,
  builder: (c) => SafeArea(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            title,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
        ),
        for (final s in sizes)
          ListTile(
            title: Text(s.$2),
            trailing: current == s.$1 ? const Icon(Icons.check) : null,
            onTap: () => Navigator.pop(c, s.$1),
          ),
      ],
    ),
  ),
);

class BrandModelsScreen extends StatefulWidget {
  const BrandModelsScreen({super.key, required this.brand});
  final Map brand;

  @override
  State<BrandModelsScreen> createState() => _BrandModelsScreenState();
}

class _BrandModelsScreenState extends State<BrandModelsScreen> {
  List<dynamic>? _models;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final m = await _api.get('car-models/', {'brand': widget.brand['id']});
    if (mounted) setState(() => _models = m as List);
  }

  Future<void> _run(Future<void> Function() f) async {
    try {
      await f();
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.brand['name_ar']}')),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.add),
        label: const Text('موديل'),
        onPressed: () async {
          final name = await askText(
            context,
            'اسم الموديل',
            hint: 'مثلاً Tiggo 9',
          );
          if (name == null || !context.mounted) return;
          final size = await pickSize(context, 'حجم $name');
          if (size == null) return;
          _run(
            () => _api.post('car-models/', {
              'brand': widget.brand['id'],
              'name': name,
              'size_class': size,
            }),
          );
        },
      ),
      body: _models == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
              children: [
                Card(
                  child: SwitchListTile(
                    value: widget.brand['is_active'] == true,
                    title: const Text('الماركة ظاهرة للعملاء'),
                    onChanged: (v) => _run(() async {
                      await _api.patch('car-brands/${widget.brand['id']}/', {
                        'is_active': v,
                      });
                      widget.brand['is_active'] = v;
                    }),
                  ),
                ),
                const SizedBox(height: 8),
                for (final m in _models!)
                  Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(
                        '${m['name']}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text(sizeLabel('${m['size_class']}')),
                      leading: Switch(
                        value: m['is_active'] == true,
                        onChanged: (v) => _run(
                          () => _api.patch('car-models/${m['id']}/', {
                            'is_active': v,
                          }),
                        ),
                      ),
                      trailing: const Icon(Icons.straighten),
                      onTap: () async {
                        final s = await pickSize(
                          context,
                          'حجم ${m['name']}',
                          '${m['size_class']}',
                        );
                        if (s != null) {
                          _run(
                            () => _api.patch('car-models/${m['id']}/', {
                              'size_class': s,
                            }),
                          );
                        }
                      },
                    ),
                  ),
                const Muted(
                  'دوس على الموديل عشان تغير حجمه. الحجم بيحدد السعر والمدة.',
                ),
              ],
            ),
    );
  }
}

/// Cars whose model was not in the list ("my model isn't listed").
class UnlistedCarsScreen extends StatefulWidget {
  const UnlistedCarsScreen({super.key});

  @override
  State<UnlistedCarsScreen> createState() => _UnlistedCarsScreenState();
}

class _UnlistedCarsScreenState extends State<UnlistedCarsScreen> {
  List<dynamic>? _cars;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final c = await _api.get('unlisted-cars/');
    if (mounted) setState(() => _cars = c as List);
  }

  Future<void> _addAsNew(Map car) async {
    final size = await pickSize(
      context,
      'حجم «${car['unlisted_model_name']}»',
      '${car['size_class']}',
    );
    if (size == null) return;
    await _api.post('unlisted-cars/${car['id']}/review/', {
      'new_model_name': car['unlisted_model_name'],
      'size_class': size,
    });
    _load();
  }

  Future<void> _link(Map car) async {
    final m = await showSearchPicker(
      context,
      title: 'اختار الموديل الصح',
      load: (q) async {
        final rows =
            await _api.get('car-models/', {'brand': car['brand'], 'search': q})
                as List;
        return [
          for (final r in rows)
            PickItem(
              r['id'],
              '${r['name']}',
              subtitle: sizeLabel('${r['size_class']}'),
            ),
        ];
      },
    );
    if (m == null) return;
    await _api.post('unlisted-cars/${car['id']}/review/', {'model': m.id});
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('موديلات محتاجة مراجعة')),
      body: _cars == null
          ? const Loading()
          : _cars!.isEmpty
          ? const EmptyState(
              icon: Icons.check_circle_outline,
              text: 'مفيش موديلات مستنية.',
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                for (final c in _cars!)
                  Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            '${c['brand_name']} • ${c['unlisted_model_name']} ${c['year']}',
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          Muted(
                            'العميل اختار الحجم: ${sizeLabel('${c['size_class']}')}',
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: BusyButton(
                                  label: 'ضيفه للقايمة',
                                  onPressed: () => _addAsNew(c),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: BusyButton(
                                  label: 'ده موديل موجود',
                                  outlined: true,
                                  onPressed: () => _link(c),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                const Muted(
                  'كل العربيات اللي ليها نفس اسم الموديل بتتربط مرة واحدة.',
                ),
              ],
            ),
    );
  }
}
