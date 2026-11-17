import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/session.dart';
import '../core/theme.dart';

/// Before/after photos (protected files, loaded with the login token). Tap to enlarge.
class PhotoGrid extends StatelessWidget {
  const PhotoGrid({super.key, required this.photos});
  final List<dynamic> photos;

  @override
  Widget build(BuildContext context) {
    const sides = {
      'front': 'قدام',
      'back': 'ورا',
      'left': 'شمال',
      'right': 'يمين',
    };
    final api = context.read<Session>().api;
    return GridView.count(
      crossAxisCount: 4,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 6,
      crossAxisSpacing: 6,
      children: [
        for (final p in photos)
          Column(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => showDialog(
                    context: context,
                    builder: (_) => Dialog(
                      child: FutureBuilder<Uint8List>(
                        future: api.bytes('${p['url']}'),
                        builder: (_, snap) => snap.hasData
                            ? InteractiveViewer(child: Image.memory(snap.data!))
                            : const SizedBox(height: 200),
                      ),
                    ),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: FutureBuilder<Uint8List>(
                      future: api.bytes('${p['url']}'),
                      builder: (_, snap) => snap.hasData
                          ? Image.memory(
                              snap.data!,
                              fit: BoxFit.cover,
                              width: double.infinity,
                            )
                          : Container(color: BrandColors.razaz),
                    ),
                  ),
                ),
              ),
              Text(
                '${p['stage'] == 'before' ? 'قبل' : 'بعد'} • ${sides[p['side']]}',
                style: const TextStyle(fontSize: 10),
              ),
            ],
          ),
      ],
    );
  }
}
