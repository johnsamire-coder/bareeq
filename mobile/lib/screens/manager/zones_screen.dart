import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

const _tiles =
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png'; // TEMPORARY until the Google Maps key

List<LatLng> _points(Map z) => [
  for (final p in z['polygon'] as List)
    LatLng((p[0] as num).toDouble(), (p[1] as num).toDouble()),
];

/// Service zones: open/close, priority, draw or edit the shape.
class ZonesScreen extends StatefulWidget {
  const ZonesScreen({super.key});

  @override
  State<ZonesScreen> createState() => _ZonesScreenState();
}

class _ZonesScreenState extends State<ZonesScreen> {
  List<dynamic>? _zones;
  Object? _error;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final z = await _api.get('zones/');
      setState(() => (_zones = z as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _open([Map? zone]) async {
    final saved = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ZoneEditorScreen(zone: zone, others: _zones!),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('المناطق')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(),
        icon: const Icon(Icons.draw_outlined),
        label: const Text('منطقة جديدة'),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _zones == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
              children: [
                SizedBox(
                  height: 220,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: FlutterMap(
                      options: const MapOptions(
                        initialCenter: LatLng(30.13, 31.48),
                        initialZoom: 10.3,
                      ),
                      children: [
                        TileLayer(
                          urlTemplate: _tiles,
                          userAgentPackageName: 'eg.bareeq.app',
                        ),
                        PolygonLayer(
                          polygons: [
                            for (final z in _zones!)
                              Polygon(
                                points: _points(z),
                                color:
                                    (z['is_active'] == true
                                            ? BrandColors.mayya
                                            : BrandColors.muted)
                                        .withValues(alpha: 0.25),
                                borderColor: z['is_active'] == true
                                    ? BrandColors.mayya
                                    : BrandColors.muted,
                                borderStrokeWidth: 2,
                                label: '${z['name']}',
                                labelStyle: const TextStyle(
                                  fontFamily: 'Cairo',
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: BrandColors.layl,
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                for (final z in _zones!)
                  Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: Switch(
                        value: z['is_active'] == true,
                        onChanged: (v) async {
                          try {
                            await _api.patch('zones/${z['id']}/', {
                              'is_active': v,
                            });
                            _load();
                          } catch (e) {
                            if (context.mounted) showError(context, e);
                          }
                        },
                      ),
                      title: Text(
                        '${z['name']}',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      subtitle: Text(
                        '${(z['polygon'] as List).length} نقط • الأولوية ${z['sort_order']}',
                      ),
                      trailing: const Icon(Icons.edit_outlined),
                      onTap: () => _open(z),
                    ),
                  ),
                const Muted(
                  'المنطقة المقفولة مبتظهرش للعملاء ومبيتحجزش فيها. لو منطقتين داخلين في بعض، الأقل في رقم الأولوية هي اللي بتتحسب.',
                ),
              ],
            ),
    );
  }
}

/// Draw a zone: tap the corners in order. Drag a corner to move it. Tap a small
/// "+" in the middle of a side to add a corner there. "Undo" removes the last change.
class ZoneEditorScreen extends StatefulWidget {
  const ZoneEditorScreen({super.key, this.zone, required this.others});
  final Map? zone;
  final List<dynamic> others;

  @override
  State<ZoneEditorScreen> createState() => _ZoneEditorScreenState();
}

class _ZoneEditorScreenState extends State<ZoneEditorScreen> {
  final _map = MapController();
  final _mapKey = GlobalKey();
  late List<LatLng> _pts = widget.zone == null ? [] : _points(widget.zone!);
  final List<List<LatLng>> _history = [];
  late final _name = TextEditingController(
    text: '${widget.zone?['name'] ?? ''}',
  );
  int? _dragging;

  void _remember() => _history.add(List.of(_pts));

  void _undo() {
    if (_history.isEmpty) return;
    setState(() => _pts = _history.removeLast());
  }

  LatLng _toLatLng(Offset global) {
    final box = _mapKey.currentContext!.findRenderObject() as RenderBox;
    return _map.camera.screenOffsetToLatLng(box.globalToLocal(global));
  }

  Future<void> _save() async {
    final api = context.read<Session>().api;
    final polygon = [
      for (final p in _pts)
        [
          double.parse(p.latitude.toStringAsFixed(6)),
          double.parse(p.longitude.toStringAsFixed(6)),
        ],
    ];
    final preview = await api.post('zones/preview/', {
      'polygon': polygon,
      'zone': widget.zone?['id'],
    });
    if (!mounted) return;
    final overlaps = (preview['overlaps_with'] as List).join('، ');
    final drop = preview['addresses_dropping_out'] as int;
    final ok = await confirmDialog(
      context,
      'تحفظ المنطقة؟',
      'عناوين متسجلة جوا الشكل ده: ${preview['addresses_inside']}'
          '${drop > 0 ? '\n⚠️ $drop عنوان متسجل هيبقى برا الخدمة.' : ''}'
          '${overlaps.isNotEmpty ? '\n⚠️ داخلة في: $overlaps' : ''}',
      yes: 'احفظ',
    );
    if (!ok) return;
    final body = {'name': _name.text.trim(), 'polygon': polygon};
    if (widget.zone == null) {
      await api.post('zones/', body);
    } else {
      await api.patch('zones/${widget.zone!['id']}/', body);
    }
    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final mids = [
      for (var i = 0; i < _pts.length && _pts.length >= 3; i++)
        (
          i,
          LatLng(
            (_pts[i].latitude + _pts[(i + 1) % _pts.length].latitude) / 2,
            (_pts[i].longitude + _pts[(i + 1) % _pts.length].longitude) / 2,
          ),
        ),
    ];
    final start = _pts.isEmpty ? const LatLng(30.0729, 31.3456) : _pts.first;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.zone == null ? 'منطقة جديدة' : 'تعديل ${widget.zone!['name']}',
        ),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: TextField(
              controller: _name,
              decoration: const InputDecoration(
                labelText: 'اسم المنطقة',
                isDense: true,
              ),
              onChanged: (_) => setState(() {}),
            ),
          ),
          Expanded(
            child: Stack(
              children: [
                // A drawing surface: kept out of screen-reader semantics so taps reach the map itself.
                ExcludeSemantics(
                  child: FlutterMap(
                    key: _mapKey,
                    mapController: _map,
                    options: MapOptions(
                      initialCenter: start,
                      initialZoom: 13,
                      interactionOptions: InteractionOptions(
                        flags: _dragging == null
                            ? InteractiveFlag.all
                            : InteractiveFlag.none,
                      ),
                      onTap: (_, p) => setState(() {
                        _remember();
                        _pts.add(p);
                      }),
                    ),
                    children: [
                      TileLayer(
                        urlTemplate: _tiles,
                        userAgentPackageName: 'eg.bareeq.app',
                      ),
                      PolygonLayer(
                        polygons: [
                          for (final z in widget.others)
                            if (z['id'] != widget.zone?['id'])
                              Polygon(
                                points: _points(z),
                                color: BrandColors.muted.withValues(
                                  alpha: 0.15,
                                ),
                                borderColor: BrandColors.muted,
                                borderStrokeWidth: 1,
                              ),
                          if (_pts.length >= 3)
                            Polygon(
                              points: _pts,
                              color: BrandColors.mayya.withValues(alpha: 0.25),
                              borderColor: BrandColors.mayya,
                              borderStrokeWidth: 3,
                            ),
                        ],
                      ),
                      if (_pts.length == 2)
                        PolylineLayer(
                          polylines: [
                            Polyline(
                              points: _pts,
                              color: BrandColors.mayya,
                              strokeWidth: 3,
                            ),
                          ],
                        ),
                      MarkerLayer(
                        markers: [
                          for (final (i, p) in mids)
                            Marker(
                              point: p,
                              width: 28,
                              height: 28,
                              child: GestureDetector(
                                onTap: () => setState(() {
                                  _remember();
                                  _pts.insert(i + 1, p);
                                }),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: BrandColors.mayya,
                                    ),
                                  ),
                                  child: const Icon(
                                    Icons.add,
                                    size: 16,
                                    color: BrandColors.mayya,
                                  ),
                                ),
                              ),
                            ),
                          for (var i = 0; i < _pts.length; i++)
                            Marker(
                              point: _pts[i],
                              width: 34,
                              height: 34,
                              child: GestureDetector(
                                onPanStart: (_) => setState(() {
                                  _remember();
                                  _dragging = i;
                                }),
                                onPanUpdate: (d) => setState(
                                  () => _pts[i] = _toLatLng(d.globalPosition),
                                ),
                                onPanEnd: (_) =>
                                    setState(() => _dragging = null),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: _dragging == i
                                        ? BrandColors.lamaa
                                        : BrandColors.layl,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: Colors.white,
                                      width: 3,
                                    ),
                                  ),
                                  alignment: Alignment.center,
                                  child: Text(
                                    '${i + 1}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SimpleAttributionWidget(
                        source: Text('OpenStreetMap'),
                      ),
                    ],
                  ),
                ),
                Positioned(
                  top: 10,
                  left: 10,
                  right: 10,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.95),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      _pts.length < 3
                          ? 'دوس على أركان المنطقة بالترتيب (${_pts.length} من 3 على الأقل).'
                          : 'اسحب أي ركن لمكانه، أو دوس «+» عشان تزود ركن في نص الضلع.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(12),
              // Every button inside Expanded: the theme makes buttons full-width by default.
              child: Row(
                children: [
                  SizedBox(
                    width: 56,
                    child: OutlinedButton(
                      onPressed: _history.isEmpty ? null : _undo,
                      style: OutlinedButton.styleFrom(padding: EdgeInsets.zero),
                      child: const Icon(Icons.undo, semanticLabel: 'ارجع'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _pts.isEmpty
                          ? null
                          : () => setState(() {
                              _remember();
                              _pts.clear();
                            }),
                      child: const Text('امسح'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: BusyButton(
                      label: 'احفظ',
                      onPressed:
                          _pts.length >= 3 && _name.text.trim().isNotEmpty
                          ? _save
                          : null,
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

/// "Notify me when you arrive" requests: where demand is outside our zones.
class DemandScreen extends StatefulWidget {
  const DemandScreen({super.key});

  @override
  State<DemandScreen> createState() => _DemandScreenState();
}

class _DemandScreenState extends State<DemandScreen> {
  List<dynamic>? _items;

  @override
  void initState() {
    super.initState();
    context
        .read<Session>()
        .api
        .get('area-requests/')
        .then((r) => setState(() => _items = r as List))
        .catchError((e) {
          if (mounted) showError(context, e);
        });
  }

  @override
  Widget build(BuildContext context) {
    final open = _items?.where((x) => x['notified_at'] == null).toList() ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('طلبات «بلغوني»')),
      body: _items == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  '${open.length} طلب مستني إننا نوصل',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  height: 240,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: FlutterMap(
                      options: const MapOptions(
                        initialCenter: LatLng(30.08, 31.40),
                        initialZoom: 10,
                      ),
                      children: [
                        TileLayer(
                          urlTemplate: _tiles,
                          userAgentPackageName: 'eg.bareeq.app',
                        ),
                        MarkerLayer(
                          markers: [
                            for (final r in open)
                              Marker(
                                point: LatLng(
                                  double.parse('${r['lat']}'),
                                  double.parse('${r['lng']}'),
                                ),
                                child: const Icon(
                                  Icons.location_on,
                                  color: BrandColors.danger,
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                for (final r in _items!)
                  Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(
                        '${r['area_name']}'.isEmpty
                            ? 'من غير اسم منطقة'
                            : '${r['area_name']}',
                      ),
                      subtitle: Text(
                        '${r['customer_name']} • ${r['customer_phone']}',
                      ),
                      trailing: r['notified_at'] != null
                          ? const Pill('اتبلغ')
                          : (r['now_covered_by'] != null
                                ? Pill('بقت في ${r['now_covered_by']}')
                                : const Muted('برا المناطق')),
                    ),
                  ),
                const Muted('لما تضيف منطقة تغطي أي طلب، العميل بيتبلغ لوحده.'),
              ],
            ),
    );
  }
}
