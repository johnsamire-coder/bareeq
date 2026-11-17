import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../core/theme.dart';

/// Pick one point on the map (pin fixed in the middle). Returns a LatLng.
/// TEMPORARY MAP: OpenStreetMap until the Google Maps key arrives.
class PickPointScreen extends StatefulWidget {
  const PickPointScreen({super.key, required this.title, this.start});
  final String title;
  final LatLng? start;

  @override
  State<PickPointScreen> createState() => _PickPointScreenState();
}

class _PickPointScreenState extends State<PickPointScreen> {
  late LatLng _center = widget.start ?? const LatLng(30.0729, 31.3456);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Stack(
        children: [
          FlutterMap(
            options: MapOptions(
              initialCenter: _center,
              initialZoom: 14,
              onPositionChanged: (c, _) => _center = c.center,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'eg.bareeq.app',
              ),
              const SimpleAttributionWidget(source: Text('OpenStreetMap')),
            ],
          ),
          const IgnorePointer(
            child: Center(
              child: Padding(
                padding: EdgeInsets.only(bottom: 36),
                child: Icon(
                  Icons.location_on_rounded,
                  size: 46,
                  color: BrandColors.layl,
                ),
              ),
            ),
          ),
          Positioned(
            left: 16,
            right: 16,
            bottom: 24,
            child: FilledButton(
              onPressed: () => Navigator.pop(context, _center),
              child: const Text('اختار المكان ده'),
            ),
          ),
        ],
      ),
    );
  }
}
