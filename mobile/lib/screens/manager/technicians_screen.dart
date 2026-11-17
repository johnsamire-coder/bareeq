import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/pick_point_screen.dart';

const weekdays = [5, 6, 0, 1, 2, 3, 4]; // Saturday first (server: Monday = 0)
const weekdayNames = {
  0: 'الاتنين',
  1: 'التلات',
  2: 'الأربع',
  3: 'الخميس',
  4: 'الجمعة',
  5: 'السبت',
  6: 'الحد',
};

/// Technicians: add one (by phone), stop one, open his schedule.
class TechniciansScreen extends StatefulWidget {
  const TechniciansScreen({super.key});

  @override
  State<TechniciansScreen> createState() => _TechniciansScreenState();
}

class _TechniciansScreenState extends State<TechniciansScreen> {
  List<dynamic>? _items;
  Object? _error;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await _api.get('manage/technician-schedules/');
      setState(() => (_items = r as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _add() async {
    final phone = TextEditingController(), name = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('فني جديد'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'الاسم'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: phone,
              keyboardType: TextInputType.phone,
              textDirection: TextDirection.ltr,
              decoration: const InputDecoration(labelText: 'رقم الموبايل'),
            ),
            const SizedBox(height: 8),
            const Muted('الفني بيدخل بالرقم ده والكود. مينفعش يسجل نفسه.'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d, false),
            child: const Text('رجوع'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(d, true),
            child: const Text('ضيف'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _api.post('technicians/', {
        'phone': phone.text.trim(),
        'full_name': name.text.trim(),
      });
      await _load();
      if (mounted) showInfo(context, 'اتضاف. حدد مناطقه ومواعيده.');
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الفنيين')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.person_add_alt),
        label: const Text('فني جديد'),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _items == null
          ? const Loading()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
                itemCount: _items!.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (_, i) {
                  final t = _items![i];
                  final active = t['is_active'] == true;
                  final days = (t['shifts'] as List)
                      .map((s) => weekdayNames[s['weekday']])
                      .join('، ');
                  return Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: active
                            ? BrandColors.razaz
                            : const Color(0xFFF1F3F5),
                        child: Icon(
                          Icons.engineering,
                          color: active ? BrandColors.layl : BrandColors.muted,
                        ),
                      ),
                      title: Text(
                        '${t['name']}',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      subtitle: Text(
                        active
                            ? '${t['start_label'] ?? ''}${days.isEmpty ? '\nمفيش مواعيد شغل' : '\n$days'}'
                            : 'موقوف',
                      ),
                      isThreeLine: true,
                      trailing: const Icon(Icons.chevron_left),
                      onTap: () async {
                        await Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => TechnicianScheduleScreen(
                              profileId: t['id'] as int,
                            ),
                          ),
                        );
                        _load();
                      },
                    ),
                  );
                },
              ),
            ),
    );
  }
}

/// One technician: active or stopped, zones, start point, weekly hours, days off.
class TechnicianScheduleScreen extends StatefulWidget {
  const TechnicianScheduleScreen({super.key, required this.profileId});
  final int profileId;

  @override
  State<TechnicianScheduleScreen> createState() =>
      _TechnicianScheduleScreenState();
}

class _TechnicianScheduleScreenState extends State<TechnicianScheduleScreen> {
  Map<String, dynamic>? _p;
  List<dynamic> _zones = [], _daysOff = [];
  Object? _error;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = Map<String, dynamic>.from(
        await _api.get('manage/technician-schedules/${widget.profileId}/'),
      );
      final z = await _api.get('zones/') as List;
      final off =
          await _api.get('manage/technician-days-off/', {
                'technician': widget.profileId,
              })
              as List;
      setState(() => (_p = p, _zones = z, _daysOff = off, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _patch(Map<String, dynamic> body) async {
    try {
      await _api.patch(
        'manage/technician-schedules/${widget.profileId}/',
        body,
      );
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _setActive(bool v) async {
    try {
      await _api.patch('technicians/${_p!['user']}/', {'is_active': v});
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _pickStart() async {
    final start = _p!['start_lat'] == null
        ? null
        : LatLng(
            double.parse('${_p!['start_lat']}'),
            double.parse('${_p!['start_lng']}'),
          );
    final point = await Navigator.push<LatLng>(
      context,
      MaterialPageRoute(
        builder: (_) =>
            PickPointScreen(title: 'نقطة بداية الفني', start: start),
      ),
    );
    if (point == null || !mounted) return;
    final label = await askText(
      context,
      'اسم المكان',
      hint: 'مثلاً: المحل، البيت',
      required: false,
    );
    await _patch({
      'start_lat': point.latitude.toStringAsFixed(6),
      'start_lng': point.longitude.toStringAsFixed(6),
      'start_label': (label ?? '').isEmpty ? 'نقطة البداية' : label,
    });
  }

  Map? _shift(int weekday) {
    for (final s in _p!['shifts'] as List) {
      if (s['weekday'] == weekday) return s;
    }
    return null;
  }

  String _hhmm(TimeOfDay t) =>
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  TimeOfDay _parse(String s) => TimeOfDay(
    hour: int.parse(s.substring(0, 2)),
    minute: int.parse(s.substring(3, 5)),
  );
  String _show(String s) => clock(
    DateTime(
      2026,
      1,
      1,
      int.parse(s.substring(0, 2)),
      int.parse(s.substring(3, 5)),
    ),
  );

  Future<void> _toggleDay(int weekday, bool on) async {
    try {
      final s = _shift(weekday);
      if (on && s == null) {
        await _api.post('manage/technician-shifts/', {
          'technician': widget.profileId,
          'weekday': weekday,
          'start_time': '09:00',
          'end_time': '22:00',
        });
      } else if (!on && s != null) {
        await _api.delete('manage/technician-shifts/${s['id']}/');
      }
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _editTime(Map s, String field) async {
    final t = await showTimePicker(
      context: context,
      initialTime: _parse('${s[field]}'),
    );
    if (t == null) return;
    try {
      await _api.patch('manage/technician-shifts/${s['id']}/', {
        field: _hhmm(t),
      });
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _addDayOff() async {
    final d = await showDatePicker(
      context: context,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (d == null || !mounted) return;
    final reason = await askText(
      context,
      'سبب الإجازة',
      hint: 'اختياري',
      required: false,
    );
    if (reason == null) return;
    try {
      await _api.post('manage/technician-days-off/', {
        'technician': widget.profileId,
        'reason': reason,
        'date':
            '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}',
      });
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${_p?['name'] ?? 'الفني'}')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _p == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: SwitchListTile(
                    value: _p!['is_active'] == true,
                    onChanged: _setActive,
                    title: const Text(
                      'شغال',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    subtitle: Text(
                      '${_p!['phone']}  •  لو وقفته، مبيتوزعلوش طلبات ومبيقدرش يدخل.',
                    ),
                  ),
                ),
                const SectionTitle('المناطق اللي بيغطيها'),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final z in _zones)
                      FilterChip(
                        label: Text('${z['name']}'),
                        selected: (_p!['zones'] as List).contains(z['id']),
                        onSelected: (v) {
                          final ids = (_p!['zones'] as List)
                              .cast<int>()
                              .toSet();
                          v ? ids.add(z['id'] as int) : ids.remove(z['id']);
                          _patch({'zones': ids.toList()});
                        },
                      ),
                  ],
                ),
                const SectionTitle('نقطة البداية'),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.home_work_outlined),
                    title: Text(
                      _p!['start_lat'] == null
                          ? 'لسه متحددتش (مش هيتوزعله طلبات)'
                          : '${_p!['start_label']}',
                    ),
                    subtitle: _p!['start_lat'] == null
                        ? null
                        : Text(
                            '${_p!['start_lat']}, ${_p!['start_lng']}',
                            textDirection: TextDirection.ltr,
                          ),
                    trailing: const Icon(Icons.edit_location_alt_outlined),
                    onTap: _pickStart,
                  ),
                ),
                const SectionTitle('مواعيد الشغل'),
                Card(
                  child: Column(
                    children: [
                      for (final wd in weekdays)
                        Builder(
                          builder: (_) {
                            final s = _shift(wd);
                            return ListTile(
                              dense: true,
                              leading: Switch(
                                value: s != null,
                                onChanged: (v) => _toggleDay(wd, v),
                              ),
                              title: Text(
                                weekdayNames[wd]!,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              trailing: s == null
                                  ? const Muted('إجازة')
                                  : Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        TextButton(
                                          onPressed: () =>
                                              _editTime(s, 'start_time'),
                                          child: Text(
                                            _show('${s['start_time']}'),
                                          ),
                                        ),
                                        const Text('لـ'),
                                        TextButton(
                                          onPressed: () =>
                                              _editTime(s, 'end_time'),
                                          child: Text(
                                            _show('${s['end_time']}'),
                                          ),
                                        ),
                                      ],
                                    ),
                            );
                          },
                        ),
                    ],
                  ),
                ),
                SectionTitle(
                  'إجازات بتاريخ',
                  trailing: TextButton.icon(
                    onPressed: _addDayOff,
                    icon: const Icon(Icons.add),
                    label: const Text('إجازة'),
                  ),
                ),
                if (_daysOff.isEmpty) const Muted('مفيش.'),
                for (final d in _daysOff)
                  Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text('${d['date']}'),
                      subtitle: '${d['reason']}'.isEmpty
                          ? null
                          : Text('${d['reason']}'),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete_outline),
                        onPressed: () async {
                          await _api.delete(
                            'manage/technician-days-off/${d['id']}/',
                          );
                          _load();
                        },
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}
