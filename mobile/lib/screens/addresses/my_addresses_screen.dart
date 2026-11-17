import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';
import 'add_address_screen.dart';

class MyAddressesScreen extends StatefulWidget {
  const MyAddressesScreen({super.key});

  @override
  State<MyAddressesScreen> createState() => _MyAddressesScreenState();
}

class _MyAddressesScreenState extends State<MyAddressesScreen> {
  List<dynamic>? _items;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('my-addresses/');
      setState(() => (_items = r as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _add() async {
    final a = await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AddAddressScreen()),
    );
    if (a != null) _load();
  }

  Future<void> _remove(Map a) async {
    if (!await confirmDialog(context, 'تشيل العنوان؟', '${a['label']}')) return;
    if (!mounted) return;
    try {
      await context.read<Session>().api.delete('my-addresses/${a['id']}/');
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('عناويني')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.add_location_alt_outlined),
        label: const Text('ضيف عنوان'),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _items == null
          ? const Loading()
          : _items!.isEmpty
          ? const EmptyState(
              icon: Icons.location_off_outlined,
              text: 'لسه مضفتش عناوين.',
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: _items!.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (_, i) {
                final a = _items![i];
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.location_on_outlined, size: 30),
                    title: Text(
                      '${a['label']}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    subtitle: Text(addressLine(a)),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () => _remove(a),
                    ),
                  ),
                );
              },
            ),
    );
  }
}

String addressLine(Map a) {
  final parts = <String>[
    if ((a['zone'] ?? {})['name'] != null) '${a['zone']['name']}',
    if ('${a['street'] ?? ''}'.isNotEmpty) '${a['street']}',
    'عمارة ${a['building']}',
    if ('${a['floor'] ?? ''}'.isNotEmpty) 'دور ${a['floor']}',
    if ('${a['landmark'] ?? ''}'.isNotEmpty) '${a['landmark']}',
  ];
  return parts.join(' • ');
}
