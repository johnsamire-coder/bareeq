import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../widgets/common.dart';

/// The technician types only the quantity of each material (list and prices are the manager's).
class MaterialsScreen extends StatefulWidget {
  const MaterialsScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<MaterialsScreen> createState() => _MaterialsScreenState();
}

class _MaterialsScreenState extends State<MaterialsScreen> {
  List<dynamic>? _materials;
  final Map<int, TextEditingController> _qty = {};

  @override
  void initState() {
    super.initState();
    context
        .read<Session>()
        .api
        .get('technician/materials/')
        .then((m) {
          setState(() {
            _materials = m as List;
            for (final x in _materials!) {
              _qty[x['id'] as int] = TextEditingController();
            }
          });
        })
        .catchError((e) {
          if (mounted) showError(context, e);
        });
  }

  Future<void> _save() async {
    final items = [
      for (final e in _qty.entries)
        if (e.value.text.trim().isNotEmpty &&
            double.tryParse(e.value.text.trim()) != 0)
          {'material': e.key, 'quantity': e.value.text.trim()},
    ];
    final r = await context.read<Session>().api.post(
      'technician/jobs/${widget.orderId}/materials/',
      {'items': items},
    );
    if (!mounted) return;
    showInfo(context, 'اتسجلت. التكلفة ${money(r['materials_cost'])}');
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الخامات')),
      body: _materials == null
          ? const Loading()
          : _materials!.isEmpty
          ? const EmptyState(
              icon: Icons.inventory_2_outlined,
              text: 'المدير لسه مضافش خامات.',
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Muted(
                  'اكتب الكمية اللي استخدمتها بس. اللي مستخدمتهوش سيبه فاضي.',
                ),
                const SizedBox(height: 10),
                for (final m in _materials!)
                  Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(
                        '${m['name']}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text('بالـ${m['unit_label']}'),
                      trailing: SizedBox(
                        width: 90,
                        child: TextField(
                          controller: _qty[m['id']],
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                          textAlign: TextAlign.center,
                          decoration: const InputDecoration(
                            hintText: '0',
                            isDense: true,
                          ),
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 12),
                BusyButton(label: 'احفظ', onPressed: _save),
              ],
            ),
    );
  }
}
