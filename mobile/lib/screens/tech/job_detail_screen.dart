import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/links.dart';
import '../../core/location.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../orders/status.dart';
import 'materials_screen.dart';

const sideNames = {'front': 'قدام', 'back': 'ورا', 'left': 'الجنب الشمال', 'right': 'الجنب اليمين'};

/// One job: where, who, what, and the buttons for each step.
/// Photos come ONLY from the camera (no gallery), with time and place.
class JobDetailScreen extends StatefulWidget {
  const JobDetailScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<JobDetailScreen> createState() => _JobDetailScreenState();
}

class _JobDetailScreenState extends State<JobDetailScreen> {
  Map<String, dynamic>? _j;
  Object? _error;
  String? _uploading; // "before-front" while a photo uploads

  Api get _api => context.read<Session>().api;
  String get _base => 'technician/jobs/${widget.orderId}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final j = await _api.get('$_base/');
      setState(() => (_j = Map<String, dynamic>.from(j), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<Map<String, dynamic>> _where() async {
    final p = await currentPosition();
    return p == null ? {} : {'lat': coord(p.latitude), 'lng': coord(p.longitude)};
  }

  Future<void> _step(String action) async {
    final j = await _api.post('$_base/$action/', await _where());
    setState(() => _j = Map<String, dynamic>.from(j));
  }

  Future<void> _call() async {
    await callPhone('${_j!['customer_phone']}');
    final j = await _api.post('$_base/called-customer/');
    setState(() => _j = Map<String, dynamic>.from(j));
  }

  Future<void> _carNotFound() async {
    if (!await confirmDialog(context, 'العربية مش موجودة؟', 'الطلب هيتلغي، والعميل هيتبلغ، ومكانك هيتسجل.', yes: 'أيوه، سجّل')) return;
    final where = await _where();
    if (where.isEmpty) throw ApiError('location_required', 'لازم تفتح اللوكيشن عشان نسجل مكانك.');
    final j = await _api.post('$_base/car-not-found/', where);
    setState(() => _j = Map<String, dynamic>.from(j));
  }

  Future<void> _photo(String stage, String side) async {
    final shot = await ImagePicker().pickImage(source: ImageSource.camera, preferredCameraDevice: CameraDevice.rear, maxWidth: 2400);
    if (shot == null) return;
    setState(() => _uploading = '$stage-$side');
    try {
      final bytes = await shot.readAsBytes();
      final takenAt = DateTime.now().toUtc().toIso8601String();
      final p = await currentPosition();
      if (p == null) throw ApiError('location_required', 'لازم تفتح اللوكيشن: الصورة بتتسجل بمكانها.');
      await _api.upload('$_base/photos/', {
        'stage': stage, 'side': side, 'captured_at': takenAt,
        'lat': coord(p.latitude), 'lng': coord(p.longitude), 'accuracy_m': '${p.accuracy.round()}',
      }, 'image', bytes, '$stage-$side.jpg');
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _uploading = null);
    }
  }

  Future<void> _complete() async {
    final due = _j!['amount_to_collect'] as int;
    int? cash;
    if (due > 0) {
      final c = TextEditingController(text: '${due ~/ 100}');
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('استلمت كام كاش؟'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('المطلوب: ${money(due)}'),
            const SizedBox(height: 10),
            TextField(controller: c, keyboardType: TextInputType.number, textAlign: TextAlign.center,
                decoration: const InputDecoration(suffixText: 'ج.م')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('رجوع')),
            FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('خلصت')),
          ],
        ),
      );
      if (ok != true) return;
      final pounds = int.tryParse(c.text.trim());
      if (pounds == null || pounds < 0) throw ApiError('bad_amount', 'اكتب المبلغ بالجنيه.');
      cash = pounds * 100;
    }
    final j = await _api.post('$_base/complete/', {...await _where(), 'cash_collected': ?cash});
    setState(() => _j = Map<String, dynamic>.from(j));
    if (mounted) {
      showInfo(context, 'برافو! الطلب خلص.');
      await Navigator.push(context, MaterialPageRoute(builder: (_) => MaterialsScreen(orderId: widget.orderId)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('طلب ${widget.orderId}')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _j == null
              ? const Loading()
              : RefreshIndicator(onRefresh: _load, child: _body()),
    );
  }

  Widget _photoGrid(String stage) {
    final taken = ((_j!['photo_counts'] as Map)[stage] as List).cast<String>();
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      childAspectRatio: 2.4,
      children: [
        for (final side in sideNames.keys)
          OutlinedButton(
            onPressed: _uploading == null ? () => _photo(stage, side) : null,
            style: OutlinedButton.styleFrom(
              backgroundColor: taken.contains(side) ? const Color(0xFFE3F4E5) : Colors.white,
              side: BorderSide(color: taken.contains(side) ? BrandColors.good : BrandColors.line),
            ),
            child: _uploading == '$stage-$side'
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(taken.contains(side) ? Icons.check_circle : Icons.photo_camera_outlined,
                        color: taken.contains(side) ? BrandColors.good : BrandColors.layl, size: 20),
                    const SizedBox(width: 6),
                    Text(sideNames[side]!),
                  ]),
          ),
      ],
    );
  }

  Widget _body() {
    final j = _j!;
    final status = '${j['status']}';
    final a = j['address_details'] as Map;
    final before = ((j['photo_counts'] as Map)['before'] as List).length;
    final after = ((j['photo_counts'] as Map)['after'] as List).length;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${clock(parseServerTime('${j['scheduled_start']}'))} - ${clock(parseServerTime('${j['scheduled_end']}'))}',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800))),
              statusPill(j),
            ]),
            const SizedBox(height: 8),
            Text('${j['customer_name']}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            Text('${j['zone_name']} • ${a['street']}'),
            Text('عمارة ${a['building']}${'${a['floor']}'.isNotEmpty ? ' • دور ${a['floor']}' : ''}'
                '${'${a['apartment']}'.isNotEmpty ? ' • شقة ${a['apartment']}' : ''}'),
            if ('${a['landmark']}'.isNotEmpty) Muted('علامة: ${a['landmark']}'),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: OutlinedButton.icon(onPressed: () => openDirections('${j['lat']}', '${j['lng']}'),
                  icon: const Icon(Icons.navigation_outlined), label: const Text('وديني'))),
              const SizedBox(width: 8),
              Expanded(child: OutlinedButton.icon(onPressed: () => callPhone('${j['customer_phone']}'),
                  icon: const Icon(Icons.call_outlined), label: const Text('كلّم العميل'))),
            ]),
          ]),
        ),
      ),
      const SectionTitle('الشغل'),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final item in j['items'] as List) ...[
              Text('${item['car_name']} • ${item['car_color']}${'${item['car_plate']}'.isNotEmpty ? ' • ${item['car_plate']}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              Muted('بتتركن: ${item['car_parking']}'),
              for (final line in item['quote']['lines'] as List) Text('• ${line['name']} (${duration(line['minutes'] as int)})'),
              if (item['quote']['oil'] != null) Text('• زيت: ${item['quote']['oil']['name']}'),
              const SizedBox(height: 6),
            ],
            const Divider(color: BrandColors.line),
            KeyValue('تحصّل كاش', money(j['amount_to_collect']), bold: true),
            if ((j['wallet_used'] as int) > 0) Muted('العميل دفع ${money(j['wallet_used'])} من المحفظة.'),
            if (j['payment_method'] == 'instapay') const Muted('العميل دفع InstaPay.'),
          ]),
        ),
      ),
      const SizedBox(height: 16),
      ..._actions(status, before, after),
    ]);
  }

  List<Widget> _actions(String status, int before, int after) {
    switch (status) {
      case 'confirmed':
        return [BusyButton(label: 'أنا في الطريق', icon: Icons.directions_car, onPressed: () => _step('on-the-way'))];
      case 'on_the_way':
        return [BusyButton(label: 'وصلت', icon: Icons.place, onPressed: () => _step('arrived'))];
      case 'arrived':
        final called = _j!['called_customer_at'] != null;
        return [
          const SectionTitle('صوّر العربية قبل الشغل (4 صور)'),
          _photoGrid('before'),
          const SizedBox(height: 12),
          BusyButton(label: 'ابدأ الشغل', icon: Icons.play_arrow_rounded, onPressed: before < 4 ? null : () => _step('start')),
          const SizedBox(height: 24),
          const Muted('مش لاقي العربية؟ اتصل بالعميل الأول، واستنى المدة المحددة.'),
          const SizedBox(height: 8),
          BusyButton(label: called ? 'اتصلت تاني' : 'اتصلت بالعميل', outlined: true, icon: Icons.phone_forwarded, onPressed: _call),
          const SizedBox(height: 8),
          BusyButton(label: 'العربية مش موجودة', outlined: true, icon: Icons.report_gmailerrorred, onPressed: called ? _carNotFound : null),
        ];
      case 'in_progress':
        return [
          const SectionTitle('صوّر العربية بعد الشغل (4 صور)'),
          _photoGrid('after'),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => MaterialsScreen(orderId: widget.orderId))),
            icon: const Icon(Icons.inventory_2_outlined),
            label: Text((_j!['materials_cost'] ?? 0) == 0 ? 'سجّل الخامات' : 'الخامات'),
          ),
          const SizedBox(height: 8),
          BusyButton(label: 'خلصت الشغل', icon: Icons.check_rounded, onPressed: after < 4 ? null : _complete),
        ];
      case 'completed':
        return [
          const EmptyState(icon: Icons.verified_rounded, text: 'الطلب خلص.'),
          OutlinedButton.icon(
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => MaterialsScreen(orderId: widget.orderId))),
            icon: const Icon(Icons.inventory_2_outlined),
            label: const Text('الخامات'),
          ),
        ];
      default:
        return [EmptyState(icon: Icons.info_outline, text: '${_j!['status_label']}')];
    }
  }
}
