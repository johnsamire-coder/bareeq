import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

const _tiles =
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png'; // TEMPORARY until the Google Maps key

/// The technician on the map while he is on the way, with a rough arrival time.
class TrackingCard extends StatefulWidget {
  const TrackingCard({super.key, required this.orderId});
  final int orderId;

  @override
  State<TrackingCard> createState() => _TrackingCardState();
}

class _TrackingCardState extends State<TrackingCard> {
  Map<String, dynamic>? _t;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get(
        'orders/${widget.orderId}/tracking/',
      );
      if (!mounted) return;
      setState(() => _t = Map<String, dynamic>.from(r));
      if (_t!['active'] == true) {
        _timer = Timer(
          Duration(seconds: (_t!['interval_seconds'] ?? 30) as int),
          _load,
        );
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    if (t == null || t['active'] != true) return const SizedBox.shrink();
    final has = t['lat'] != null;
    return Card(
      color: BrandColors.razaz,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              has
                  ? '${t['technician_name']} في الطريق، يوصل خلال حوالي ${t['eta_minutes']} دقيقة'
                  : '${t['technician_name']} في الطريق ليك',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            if (has) ...[
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: SizedBox(
                  height: 200,
                  child: ExcludeSemantics(
                    child: FlutterMap(
                      options: MapOptions(
                        initialCenter: LatLng(
                          t['lat'] as double,
                          t['lng'] as double,
                        ),
                        initialZoom: 14,
                      ),
                      children: [
                        TileLayer(
                          urlTemplate: _tiles,
                          userAgentPackageName: 'eg.bareeq.app',
                        ),
                        MarkerLayer(
                          markers: [
                            Marker(
                              point: LatLng(
                                t['lat'] as double,
                                t['lng'] as double,
                              ),
                              width: 44,
                              height: 44,
                              child: const CircleAvatar(
                                backgroundColor: BrandColors.lamaa,
                                child: Icon(
                                  Icons.directions_car,
                                  color: BrandColors.layl,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 4),
              const Muted('الوقت تقريبي.'),
            ],
          ],
        ),
      ),
    );
  }
}
