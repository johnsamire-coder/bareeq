import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';

/// Supervisors: add one with his phone, choose his zones, stop him.
class SupervisorsScreen extends StatefulWidget {
  const SupervisorsScreen({super.key});

  @override
  State<SupervisorsScreen> createState() => _SupervisorsScreenState();
}

class _SupervisorsScreenState extends State<SupervisorsScreen> {
  List<dynamic>? _rows;
  List<dynamic> _zones = [];
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<Session>().api;
      final rows = await api.get('manage/supervisors/') as List;
      final zones = await api.get('zones/') as List;
      setState(() => (_rows = rows, _zones = zones, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<List<int>?> _pickZones(List<int> current) async {
    final chosen = {...current};
    return showDialog<List<int>>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('مناطقه'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final z in _zones)
                CheckboxListTile(
                  value: chosen.contains(z['id']),
                  title: Text('${z['name']}'),
                  onChanged: (v) => set(
                    () => v == true
                        ? chosen.add(z['id'] as int)
                        : chosen.remove(z['id']),
                  ),
                ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(d),
              child: const Text('رجوع'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(d, chosen.toList()),
              child: const Text('احفظ'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _add() async {
    final name = TextEditingController(), phone = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('مشرف جديد'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'الاسم'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'رقم الموبايل'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d, false),
            child: const Text('رجوع'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(d, true),
            child: const Text('كمّل'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final zones = await _pickZones([]);
    if (zones == null || !mounted) return;
    await context.read<Session>().api.post('manage/supervisors/', {
      'full_name': name.text.trim(),
      'phone': phone.text.trim(),
      'zones': zones,
    });
    if (mounted) showInfo(context, 'المشرف اتضاف. يدخل برقمه والكود.');
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<Session>().api;
    return Scaffold(
      appBar: AppBar(title: const Text('المشرفين')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.add),
        label: const Text('مشرف جديد'),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _rows == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
              children: [
                const Muted(
                  'المشرف بيشوف شغل مناطقه بس: طلبات اليوم، والخريطة، ونقل طلب لفني تاني، '
                  'والتقييمات الوحشة، وبلاغات الضرر. مالوش علاقة بالفلوس ولا الأسعار ولا الإعدادات.',
                ),
                const SizedBox(height: 8),
                if (_rows!.isEmpty) const Muted('مفيش مشرفين لسه.'),
                for (final s in _rows!)
                  Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text('${s['full_name']}'),
                      subtitle: Text(
                        '‎${s['phone']}\n${(s['zones'] as List).map((z) => z['name']).join('، ')}'
                        '${s['is_active'] == true ? '' : '\nموقوف'}',
                      ),
                      isThreeLine: true,
                      trailing: PopupMenuButton<String>(
                        onSelected: (v) async {
                          if (v == 'zones') {
                            final z = await _pickZones([
                              for (final x in s['zones'] as List)
                                x['id'] as int,
                            ]);
                            if (z == null) return;
                            await api.patch('manage/supervisors/${s['id']}/', {
                              'zones': z,
                            });
                          } else {
                            await api.patch('manage/supervisors/${s['id']}/', {
                              'is_active': s['is_active'] != true,
                            });
                          }
                          _load();
                        },
                        itemBuilder: (_) => [
                          const PopupMenuItem(
                            value: 'zones',
                            child: Text('غيّر المناطق'),
                          ),
                          PopupMenuItem(
                            value: 'active',
                            child: Text(
                              s['is_active'] == true ? 'وقّفه' : 'رجّعه',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}
