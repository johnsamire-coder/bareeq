import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';
import 'add_car_screen.dart';

class MyCarsScreen extends StatefulWidget {
  const MyCarsScreen({super.key});

  @override
  State<MyCarsScreen> createState() => _MyCarsScreenState();
}

class _MyCarsScreenState extends State<MyCarsScreen> {
  List<dynamic>? _cars;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await context.read<Session>().api.get('my-cars/');
      setState(() => (_cars = c as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _add() async {
    final car = await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddCarScreen()));
    if (car != null) _load();
  }

  Future<void> _remove(Map c) async {
    if (!await confirmDialog(context, 'تشيل العربية؟', '${c['display_name']}')) return;
    if (!mounted) return;
    try {
      await context.read<Session>().api.delete('my-cars/${c['id']}/');
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('عربياتي')),
      floatingActionButton: FloatingActionButton.extended(onPressed: _add, icon: const Icon(Icons.add), label: const Text('ضيف عربية')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _cars == null
              ? const Loading()
              : _cars!.isEmpty
                  ? const EmptyState(icon: Icons.directions_car_outlined, text: 'لسه مضفتش عربيات.')
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _cars!.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 10),
                      itemBuilder: (_, i) {
                        final c = _cars![i];
                        return Card(
                          child: ListTile(
                            leading: const Icon(Icons.directions_car_filled_rounded, size: 32),
                            title: Text('${c['display_name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                            subtitle: Text('${c['color_name']}${c['plate_number'] != '' ? ' • ${c['plate_number']}' : ''}'
                                '${c['needs_review'] == true ? '\nالموديل بيتراجع' : ''}'),
                            trailing: IconButton(icon: const Icon(Icons.delete_outline), onPressed: () => _remove(c)),
                          ),
                        );
                      },
                    ),
    );
  }
}
