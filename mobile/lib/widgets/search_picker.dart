import 'dart:async';

import 'package:flutter/material.dart';

import '../core/theme.dart';
import 'common.dart';

class PickItem {
  PickItem(this.id, this.label, {this.subtitle, this.special = false});
  final Object id;
  final String label;
  final String? subtitle;
  final bool special; // e.g. "my model isn't listed"
}

/// Searchable list in a bottom sheet. `load` is called with the search text.
Future<PickItem?> showSearchPicker(
  BuildContext context, {
  required String title,
  required Future<List<PickItem>> Function(String query) load,
  bool searchable = true,
}) {
  return showModalBottomSheet<PickItem>(
    context: context,
    isScrollControlled: true,
    backgroundColor: BrandColors.sahab,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (_) => FractionallySizedBox(
      heightFactor: 0.85,
      child: _Picker(title: title, load: load, searchable: searchable),
    ),
  );
}

class _Picker extends StatefulWidget {
  const _Picker({
    required this.title,
    required this.load,
    required this.searchable,
  });
  final String title;
  final Future<List<PickItem>> Function(String) load;
  final bool searchable;

  @override
  State<_Picker> createState() => _PickerState();
}

class _PickerState extends State<_Picker> {
  List<PickItem>? _items;
  Object? _error;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _fetch('');
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _fetch(String q) async {
    try {
      final items = await widget.load(q);
      if (mounted) setState(() => (_items = items, _error = null));
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        children: [
          const SizedBox(height: 10),
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: BrandColors.line,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(14),
            child: Text(
              widget.title,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
          ),
          if (widget.searchable)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: TextField(
                autofocus: false,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: 'دوّر بالعربي أو الإنجليزي',
                ),
                onChanged: (q) {
                  _debounce?.cancel();
                  _debounce = Timer(
                    const Duration(milliseconds: 300),
                    () => _fetch(q),
                  );
                },
              ),
            ),
          const SizedBox(height: 8),
          Expanded(
            child: _error != null
                ? ErrorRetry(error: _error!, onRetry: () => _fetch(''))
                : _items == null
                ? const Loading()
                : ListView.separated(
                    itemCount: _items!.length,
                    separatorBuilder: (_, _) =>
                        const Divider(height: 1, color: BrandColors.line),
                    itemBuilder: (_, i) {
                      final it = _items![i];
                      return ListTile(
                        title: Text(
                          it.label,
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            color: it.special ? BrandColors.mayya : null,
                          ),
                        ),
                        subtitle: it.subtitle == null
                            ? null
                            : Text(it.subtitle!),
                        trailing: const Icon(Icons.chevron_left),
                        onTap: () => Navigator.pop(context, it),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
