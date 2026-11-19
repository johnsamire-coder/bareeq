import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/terms_text.dart';
import 'pricing_screens.dart';

const groupNames = {
  'scheduling': 'المواعيد',
  'login': 'الدخول',
  'cancellation': 'الإلغاء والتأجيل',
  'cars': 'العربيات',
  'services': 'الخدمات',
  'photos': 'الصور',
  'payments': 'الدفع',
  'wallet': 'المحفظة',
  'loyalty': 'الولاء والمكافآت',
  'subscriptions': 'الاشتراك الشهري',
  'fees': 'الطلب السريع ورسوم المسافة',
  'tracking': 'التتبع والتقارير',
  'notifications': 'الإشعارات',
  'ratings': 'التقييم',
};

String settingValue(Map s) {
  final v = s['value'];
  if (v == null) return 'فاضي';
  switch (s['value_type']) {
    case 'money':
      return money(v as int);
    case 'minutes':
      return duration(v as int);
    case 'hours':
      return '$v ساعة';
    case 'days':
      return '$v يوم';
    case 'percent':
      return '$v%';
    case 'boolean':
      return v == true ? 'نعم' : 'لا';
    default:
      return '$v';
  }
}

/// The settings table: every business number, edited in its own unit.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  List<dynamic>? _rows;
  Map<String, dynamic>? _terms;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final rows = await _api.get('settings/') as List;
    final t = Map<String, dynamic>.from(await _api.get('terms/status/'));
    if (mounted) setState(() => (_rows = rows, _terms = t));
  }

  Future<void> _edit(Map s) async {
    dynamic value;
    final type = '${s['value_type']}';
    if (type == 'boolean') {
      value = !(s['value'] as bool);
    } else if (type == 'money') {
      value = await askPounds(context, '${s['label']}', s['value'] as int);
    } else {
      final c = TextEditingController(text: '${s['value'] ?? ''}');
      final r = await showDialog<String>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('${s['label']}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if ('${s['description']}'.isNotEmpty)
                Muted('${s['description']}'),
              const SizedBox(height: 8),
              TextField(
                controller: c,
                autofocus: true,
                maxLines: type == 'text' ? 4 : 1,
                keyboardType: type == 'text' ? null : TextInputType.number,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(d),
              child: const Text('رجوع'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(d, c.text.trim()),
              child: const Text('احفظ'),
            ),
          ],
        ),
      );
      if (r == null) return;
      if (r.isEmpty && s['allow_empty'] == true) {
        await _save(s, null);
        return;
      }
      value = type == 'text' ? r : int.tryParse(r);
      if (value == null) throw ApiError('bad', 'اكتب رقم صحيح.');
    }
    if (value == null) return;
    await _save(s, value);
  }

  Future<void> _save(Map s, dynamic value) async {
    await _api.patch('settings/${s['key']}/', {'value': value});
    await _load();
    if (s['key'] == 'demo-mode' && mounted) {
      await context.read<Session>().loadConfig();
    }
    if (s['mentioned_in_terms'] == true && mounted) {
      showInfo(context, 'الرقم ده مكتوب في الشروط: انشر نسخة شروط جديدة.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final groups = <String, List<dynamic>>{};
    for (final r in _rows ?? []) {
      groups.putIfAbsent('${r['group']}', () => []).add(r);
    }
    return Scaffold(
      appBar: AppBar(title: const Text('الإعدادات')),
      body: _rows == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_terms?['needs_new_version'] == true)
                  Card(
                    color: const Color(0xFFFFF7E6),
                    child: ListTile(
                      leading: const Icon(
                        Icons.warning_amber_rounded,
                        color: Color(0xFF8A5A00),
                      ),
                      title: const Text('أرقام مكتوبة في الشروط اتغيرت'),
                      subtitle: Text(
                        (_terms!['changed_settings'] as List)
                            .map((c) => c['label'])
                            .join('، '),
                      ),
                      trailing: TextButton(
                        onPressed: () async {
                          await Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const TermsManageScreen(),
                            ),
                          );
                          _load();
                        },
                        child: const Text('انشر شروط جديدة'),
                      ),
                    ),
                  ),
                for (final g in groups.entries) ...[
                  SectionTitle(groupNames[g.key] ?? g.key),
                  for (final s in g.value)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(
                          '${s['label']}',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: s['mentioned_in_terms'] == true
                            ? const Text(
                                'مكتوب في الشروط',
                                style: TextStyle(color: BrandColors.mayya),
                              )
                            : null,
                        trailing: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 140),
                          child: Text(
                            settingValue(s),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            textAlign: TextAlign.left,
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                        ),
                        onTap: () async {
                          try {
                            await _edit(s);
                          } catch (e) {
                            if (context.mounted) showError(context, e);
                          }
                        },
                      ),
                    ),
                ],
              ],
            ),
    );
  }
}

/// Terms versions; publish a new version (customers accept it in the app).
class TermsManageScreen extends StatefulWidget {
  const TermsManageScreen({super.key});

  @override
  State<TermsManageScreen> createState() => _TermsManageScreenState();
}

class _TermsManageScreenState extends State<TermsManageScreen> {
  List<dynamic>? _versions;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final v = await _api.get('manage/terms/') as List;
    if (mounted) setState(() => _versions = v);
  }

  Future<void> _newVersion() async {
    final c = TextEditingController(text: '${_versions!.first['text']}');
    final text = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (ctx) => Scaffold(
          appBar: AppBar(title: const Text('نسخة شروط جديدة')),
          body: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const Muted(
                  'عدّل الأرقام أو البنود. # عنوان، ## عنوان صغير، - بند، **كلام تقيل**.',
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: TextField(
                    controller: c,
                    maxLines: null,
                    expands: true,
                    textAlignVertical: TextAlignVertical.top,
                  ),
                ),
                const SizedBox(height: 10),
                FilledButton(
                  onPressed: () => Navigator.pop(ctx, c.text),
                  child: const Text('انشر'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (text == null || !mounted) return;
    if (!await confirmDialog(
      context,
      'تنشر النسخة الجديدة؟',
      'كل العملاء هيتطلب منهم يوافقوا عليها قبل ما يكملوا.',
    )) {
      return;
    }
    try {
      await _api.post('manage/terms/', {'text': text});
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الشروط والأحكام')),
      floatingActionButton: _versions == null
          ? null
          : FloatingActionButton.extended(
              onPressed: _newVersion,
              icon: const Icon(Icons.edit_note),
              label: const Text('نسخة جديدة'),
            ),
      body: _versions == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final v in _versions!)
                      Pill(
                        'نسخة ${v['version']} • ${shortDate(parseServerTime('${v['created_at']}'))} • وافق ${v['accepted_by']}',
                      ),
                  ],
                ),
                const SectionTitle('النسخة الحالية'),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: TermsText('${_versions!.first['text']}'),
                  ),
                ),
              ],
            ),
    );
  }
}
