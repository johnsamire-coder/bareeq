import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// Shared list + add/edit form for the manager's simple lists.
enum FieldType { text, multiline, integer, money, boolean, choice, multi, date }

typedef Options = Future<List<(Object, String)>> Function(Api api);

class FieldSpec {
  const FieldSpec(
    this.key,
    this.label,
    this.type, {
    this.options,
    this.help,
    this.required = false,
  });
  final String key;
  final String label;
  final FieldType type;
  final Options? options;
  final String? help;
  final bool required;
}

class CrudScreen extends StatefulWidget {
  const CrudScreen({
    super.key,
    required this.title,
    required this.endpoint,
    required this.fields,
    required this.itemTitle,
    this.itemSubtitle,
    this.canAdd = true,
    this.toForm,
    this.toPayload,
    this.note,
    this.newDefaults = const {},
  });
  final String title;
  final String endpoint; // e.g. 'manage/oil-types/'
  final List<FieldSpec> fields;
  final String Function(Map) itemTitle;
  final String Function(Map)? itemSubtitle;
  final bool canAdd;
  final Map<String, dynamic> Function(Map)? toForm; // server row -> form values
  final Map<String, dynamic> Function(Map<String, dynamic>)?
  toPayload; // form -> server body
  final String? note;
  final Map<String, dynamic> newDefaults;

  @override
  State<CrudScreen> createState() => _CrudScreenState();
}

class _CrudScreenState extends State<CrudScreen> {
  List<dynamic>? _items;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get(widget.endpoint);
      setState(
        () => (_items = r is List ? r : (r['results'] as List), _error = null),
      );
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _edit([Map? row]) async {
    final saved = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CrudForm(spec: widget, row: row),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      floatingActionButton: widget.canAdd
          ? FloatingActionButton.extended(
              onPressed: () => _edit(),
              icon: const Icon(Icons.add),
              label: const Text('جديد'),
            )
          : null,
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _items == null
          ? const Loading()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
                children: [
                  if (widget.note != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Muted(widget.note!),
                    ),
                  if (_items!.isEmpty)
                    const EmptyState(
                      icon: Icons.inbox_outlined,
                      text: 'لسه مفيش حاجة.',
                    ),
                  for (final row in _items!)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(
                          widget.itemTitle(row),
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            color: row['is_active'] == false
                                ? BrandColors.muted
                                : null,
                          ),
                        ),
                        subtitle: widget.itemSubtitle == null
                            ? null
                            : Text(widget.itemSubtitle!(row)),
                        trailing: row['is_active'] == false
                            ? const Pill('مقفول')
                            : const Icon(Icons.edit_outlined),
                        onTap: () => _edit(row),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class CrudForm extends StatefulWidget {
  const CrudForm({super.key, required this.spec, this.row});
  final CrudScreen spec;
  final Map? row;

  @override
  State<CrudForm> createState() => _CrudFormState();
}

class _CrudFormState extends State<CrudForm> {
  late final Map<String, dynamic> _v;
  final Map<String, TextEditingController> _text = {};
  final Map<String, List<(Object, String)>> _options = {};

  @override
  void initState() {
    super.initState();
    final row = widget.row == null
        ? Map<String, dynamic>.from(widget.spec.newDefaults)
        : Map<String, dynamic>.from(widget.row!);
    _v = widget.spec.toForm != null && widget.row != null
        ? widget.spec.toForm!(row)
        : row;
    for (final f in widget.spec.fields) {
      if ({
        FieldType.text,
        FieldType.multiline,
        FieldType.integer,
        FieldType.money,
      }.contains(f.type)) {
        final raw = _v[f.key];
        final shown = raw == null
            ? ''
            : (f.type == FieldType.money ? _pounds(raw as num) : '$raw');
        _text[f.key] = TextEditingController(text: shown);
      }
    }
    _loadOptions();
  }

  String _pounds(num piastres) => piastres % 100 == 0
      ? '${piastres ~/ 100}'
      : (piastres / 100).toStringAsFixed(2);

  Future<void> _loadOptions() async {
    final api = context.read<Session>().api;
    for (final f in widget.spec.fields) {
      if (f.options != null) {
        final o = await f.options!(api);
        if (mounted) setState(() => _options[f.key] = o);
      }
    }
  }

  Future<void> _save() async {
    final body = <String, dynamic>{};
    for (final f in widget.spec.fields) {
      switch (f.type) {
        case FieldType.text:
        case FieldType.multiline:
          body[f.key] = _text[f.key]!.text.trim();
        case FieldType.integer:
          final t = _text[f.key]!.text.trim();
          body[f.key] = t.isEmpty ? null : int.tryParse(t);
          if (t.isNotEmpty && body[f.key] == null) {
            throw ApiError('bad', '«${f.label}» لازم يبقى رقم.');
          }
        case FieldType.money:
          final p = double.tryParse(_text[f.key]!.text.trim());
          if (p == null) {
            throw ApiError('bad', '«${f.label}» لازم يبقى مبلغ بالجنيه.');
          }
          body[f.key] = (p * 100).round();
        default:
          body[f.key] = _v[f.key];
      }
      if (f.required && (body[f.key] == null || body[f.key] == '')) {
        throw ApiError('bad', '«${f.label}» مطلوب.');
      }
    }
    final payload = widget.spec.toPayload != null
        ? widget.spec.toPayload!(body)
        : body;
    final api = context.read<Session>().api;
    if (widget.row == null) {
      await api.post(widget.spec.endpoint, payload);
    } else {
      await api.patch('${widget.spec.endpoint}${widget.row!['id']}/', payload);
    }
    if (mounted) Navigator.pop(context, true);
  }

  Widget _field(FieldSpec f) {
    final help = f.help == null
        ? null
        : Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Muted(f.help!),
          );
    Widget w;
    switch (f.type) {
      case FieldType.text:
      case FieldType.multiline:
      case FieldType.integer:
      case FieldType.money:
        w = TextField(
          controller: _text[f.key],
          maxLines: f.type == FieldType.multiline ? 4 : 1,
          keyboardType: f.type == FieldType.integer || f.type == FieldType.money
              ? const TextInputType.numberWithOptions(decimal: true)
              : null,
          decoration: InputDecoration(
            labelText: f.label,
            suffixText: f.type == FieldType.money ? 'ج.م' : null,
          ),
        );
      case FieldType.boolean:
        w = Card(
          child: SwitchListTile(
            value: _v[f.key] == true,
            title: Text(f.label),
            onChanged: (v) => setState(() => _v[f.key] = v),
          ),
        );
      case FieldType.choice:
        final opts = _options[f.key] ?? [];
        w = DropdownButtonFormField<Object?>(
          initialValue: opts.any((o) => o.$1 == _v[f.key]) ? _v[f.key] : null,
          decoration: InputDecoration(labelText: f.label),
          items: [
            if (!f.required)
              const DropdownMenuItem<Object?>(value: null, child: Text('—')),
            for (final o in opts)
              DropdownMenuItem<Object?>(value: o.$1, child: Text(o.$2)),
          ],
          onChanged: (v) => setState(() => _v[f.key] = v),
        );
      case FieldType.multi:
        final selected = ((_v[f.key] ?? []) as List).toSet();
        w = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(f.label, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final o in _options[f.key] ?? <(Object, String)>[])
                  FilterChip(
                    label: Text(o.$2),
                    selected: selected.contains(o.$1),
                    onSelected: (v) => setState(() {
                      v ? selected.add(o.$1) : selected.remove(o.$1);
                      _v[f.key] = selected.toList();
                    }),
                  ),
              ],
            ),
          ],
        );
      case FieldType.date:
        final d = _v[f.key] == null
            ? null
            : DateTime.parse('${_v[f.key]}').toLocal();
        w = Card(
          child: ListTile(
            title: Text(f.label),
            subtitle: Text(
              d == null ? 'اختار' : '${d.day}/${d.month}/${d.year}',
            ),
            trailing: const Icon(Icons.edit_calendar_outlined),
            onTap: () async {
              final p = await showDatePicker(
                context: context,
                initialDate: d ?? DateTime.now().add(const Duration(days: 30)),
                firstDate: DateTime.now().subtract(const Duration(days: 1)),
                lastDate: DateTime.now().add(const Duration(days: 730)),
              );
              // end of that day, Cairo time on the phone
              if (p != null) {
                setState(
                  () => _v[f.key] = DateTime(
                    p.year,
                    p.month,
                    p.day,
                    23,
                    59,
                  ).toUtc().toIso8601String(),
                );
              }
            },
          ),
        );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [w, ?help],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.row == null ? 'جديد: ${widget.spec.title}' : 'تعديل',
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final f in widget.spec.fields) _field(f),
          const SizedBox(height: 8),
          BusyButton(label: 'احفظ', onPressed: _save),
        ],
      ),
    );
  }
}
