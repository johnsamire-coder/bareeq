import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

class RatingScreen extends StatefulWidget {
  const RatingScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<RatingScreen> createState() => _RatingScreenState();
}

class _RatingScreenState extends State<RatingScreen> {
  int _stars = 0;
  final Set<int> _tags = {};
  List<dynamic> _allTags = [];
  final _comment = TextEditingController();
  bool _callMe = false;
  final List<Uint8List> _photos = [];

  @override
  void initState() {
    super.initState();
    context
        .read<Session>()
        .api
        .get('rating-tags/')
        .then((t) => setState(() => _allTags = t as List));
  }

  bool get _bad => _stars > 0 && _stars <= 3;

  Future<void> _addPhoto() async {
    final f = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 1600,
    );
    if (f != null) {
      final b = await f.readAsBytes();
      setState(() => _photos.add(b));
    }
  }

  Future<void> _send() async {
    final api = context.read<Session>().api;
    final r = await api.post('orders/${widget.orderId}/rating/', {
      'stars': _stars,
      'tags': _tags.toList(),
      'comment': _comment.text.trim(),
      'call_requested': _bad && _callMe,
    });
    final ratingId = r['rating']['id'];
    for (var i = 0; i < _photos.length; i++) {
      await api.upload(
        'ratings/$ratingId/photos/',
        {},
        'image',
        _photos[i],
        'photo$i.jpg',
      );
    }
    if (!mounted) return;
    if (r['google_review_link'] != null) {
      await showDialog(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('شكراً على تقييمك!'),
          content: Text(
            'لو حابب، قيّمنا على جوجل ماب كمان:\n${r['google_review_link']}',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c),
              child: const Text('تمام'),
            ),
          ],
        ),
      );
    } else {
      showInfo(
        context,
        _bad
            ? 'آسفين على تجربتك. فريق بريق هيتواصل معاك.'
            : 'شكراً على تقييمك!',
      );
    }
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('قيّم الخدمة')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'إيه رأيك في الغسلة؟',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 1; i <= 5; i++)
                IconButton(
                  iconSize: 44,
                  onPressed: () => setState(() => _stars = i),
                  icon: Icon(
                    i <= _stars
                        ? Icons.star_rounded
                        : Icons.star_outline_rounded,
                    color: i <= _stars ? BrandColors.lamaa : BrandColors.line,
                  ),
                ),
            ],
          ),
          const SectionTitle('إيه اللي عجبك؟'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final t in _allTags)
                FilterChip(
                  label: Text('${t['name']}'),
                  selected: _tags.contains(t['id']),
                  onSelected: (v) => setState(
                    () => v ? _tags.add(t['id']) : _tags.remove(t['id']),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _comment,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'تعليق (اختياري)'),
          ),
          if (_bad) ...[
            const SizedBox(height: 8),
            SwitchListTile(
              value: _callMe,
              onChanged: (v) => setState(() => _callMe = v),
              title: const Text('عايز حد من بريق يكلمني'),
            ),
            OutlinedButton.icon(
              onPressed: _addPhoto,
              icon: const Icon(Icons.add_a_photo_outlined),
              label: Text(
                _photos.isEmpty
                    ? 'ضيف صور (اختياري)'
                    : '${_photos.length} صورة. ضيف كمان',
              ),
            ),
          ],
          const SizedBox(height: 20),
          BusyButton(
            label: 'ابعت التقييم',
            onPressed: _stars == 0 ? null : _send,
          ),
        ],
      ),
    );
  }
}
