import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/search_picker.dart';

/// Brand -> model -> year -> color -> where it parks. No typing, except the
/// model name when "my model isn't listed" (then the customer picks the size).
class AddCarScreen extends StatefulWidget {
  const AddCarScreen({super.key});

  @override
  State<AddCarScreen> createState() => _AddCarScreenState();
}

class _AddCarScreenState extends State<AddCarScreen> {
  PickItem? _brand;
  PickItem? _model;
  bool _unlisted = false;
  final _unlistedName = TextEditingController();
  String? _size;
  int? _year;
  Map<String, dynamic>? _color;
  String? _parking;
  final _plate = TextEditingController();
  Map<String, dynamic>? _options;
  List<dynamic> _colors = [];

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  Future<void> _loadOptions() async {
    final api = context.read<Session>().api;
    try {
      final o = await api.get('car-options/');
      final c = await api.get('car-colors/');
      setState(() {
        _options = Map<String, dynamic>.from(o);
        _colors = c as List;
      });
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _pickBrand() async {
    final api = context.read<Session>().api;
    final b = await showSearchPicker(
      context,
      title: 'الماركة',
      load: (q) async {
        final rows = await api.get('car-brands/', {'search': q}) as List;
        return [
          for (final r in rows)
            PickItem(r['id'], '${r['name_ar']}', subtitle: '${r['name_en']}'),
        ];
      },
    );
    if (b != null) {
      setState(() => (_brand = b, _model = null, _unlisted = false));
    }
  }

  Future<void> _pickModel() async {
    final api = context.read<Session>().api;
    final m = await showSearchPicker(
      context,
      title: 'الموديل',
      load: (q) async {
        final rows =
            await api.get('car-models/', {'brand': _brand!.id, 'search': q})
                as List;
        return [
          for (final r in rows) PickItem(r['id'], '${r['name']}'),
          PickItem('unlisted', 'موديلي مش موجود', special: true),
        ];
      },
    );
    if (m == null) return;
    setState(() {
      _unlisted = m.id == 'unlisted';
      _model = _unlisted ? null : m;
    });
  }

  Future<void> _pickYear() async {
    final years = (_options!['years'] as List).cast<int>();
    final y = await showSearchPicker(
      context,
      title: 'سنة الصنع',
      searchable: false,
      load: (_) async {
        return [for (final y in years) PickItem(y, '$y')];
      },
    );
    if (y != null) setState(() => _year = y.id as int);
  }

  bool get _ready =>
      _brand != null &&
      (_model != null ||
          (_unlisted &&
              _unlistedName.text.trim().isNotEmpty &&
              _size != null)) &&
      _year != null &&
      _color != null &&
      _parking != null;

  Future<void> _save() async {
    final api = context.read<Session>().api;
    final car = await api.post('my-cars/', {
      'brand': _brand!.id,
      if (_model != null) 'model': _model!.id,
      if (_unlisted) 'unlisted_model_name': _unlistedName.text.trim(),
      if (_unlisted) 'size_class': _size,
      'year': _year,
      'color': _color!['id'],
      'parking': _parking,
      'plate_number': _plate.text.trim(),
    });
    if (mounted) Navigator.pop(context, car);
  }

  Widget _choice(String label, String? value, VoidCallback? onTap) => Card(
    child: ListTile(
      enabled: onTap != null,
      title: Text(
        label,
        style: const TextStyle(fontSize: 13, color: BrandColors.muted),
      ),
      subtitle: Text(
        value ?? 'اختار',
        style: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: value == null ? BrandColors.mayya : BrandColors.layl,
        ),
      ),
      trailing: const Icon(Icons.chevron_left),
      onTap: onTap,
    ),
  );

  @override
  Widget build(BuildContext context) {
    if (_options == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('ضيف عربية')),
        body: const Loading(),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('ضيف عربية')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _choice('الماركة', _brand?.label, _pickBrand),
          const SizedBox(height: 8),
          _choice(
            'الموديل',
            _unlisted ? 'موديلي مش موجود' : _model?.label,
            _brand == null ? null : _pickModel,
          ),
          if (_unlisted) ...[
            const SizedBox(height: 8),
            TextField(
              controller: _unlistedName,
              decoration: const InputDecoration(labelText: 'اسم الموديل'),
              onChanged: (_) => setState(() {}),
            ),
            const SectionTitle('حجم العربية'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final s in _options!['sizes'] as List)
                  ChoiceChip(
                    label: Text('${s['label']}'),
                    selected: _size == s['value'],
                    onSelected: (_) => setState(() => _size = s['value']),
                  ),
              ],
            ),
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Muted('هنراجع الموديل ونضيفه للقايمة.'),
            ),
          ],
          const SizedBox(height: 8),
          _choice('سنة الصنع', _year?.toString(), _pickYear),
          const SectionTitle('اللون'),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final c in _colors)
                GestureDetector(
                  onTap: () =>
                      setState(() => _color = Map<String, dynamic>.from(c)),
                  child: Column(
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: Color(
                            int.parse(
                              'FF${'${c['hex_code']}'.substring(1)}',
                              radix: 16,
                            ),
                          ),
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: _color?['id'] == c['id']
                                ? BrandColors.mayya
                                : BrandColors.line,
                            width: _color?['id'] == c['id'] ? 3 : 1,
                          ),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${c['name']}',
                        style: const TextStyle(fontSize: 11),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SectionTitle('العربية بتتركن فين؟'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in _options!['parking'] as List)
                ChoiceChip(
                  label: Text('${p['label']}'),
                  selected: _parking == p['value'],
                  onSelected: (_) => setState(() => _parking = p['value']),
                ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _plate,
            decoration: const InputDecoration(
              labelText: 'رقم اللوحة (اختياري)',
            ),
          ),
          const SizedBox(height: 20),
          BusyButton(label: 'احفظ العربية', onPressed: _ready ? _save : null),
        ],
      ),
    );
  }
}
