import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';

/// Within the allowed hours after the wash (setting; the server checks it).
class DamageReportScreen extends StatefulWidget {
  const DamageReportScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<DamageReportScreen> createState() => _DamageReportScreenState();
}

class _DamageReportScreenState extends State<DamageReportScreen> {
  final _text = TextEditingController();
  final List<Uint8List> _photos = [];

  Future<void> _addPhoto() async {
    final f = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600);
    if (f != null) {
      final b = await f.readAsBytes();
      setState(() => _photos.add(b));
    }
  }

  Future<void> _send() async {
    final api = context.read<Session>().api;
    final r = await api.post('orders/${widget.orderId}/damage-report/', {'description': _text.text.trim()});
    for (var i = 0; i < _photos.length; i++) {
      await api.upload('damage-reports/${r['id']}/photos/', {}, 'image', _photos[i], 'photo$i.jpg');
    }
    if (!mounted) return;
    showInfo(context, 'البلاغ وصل. هنراجع صور قبل وبعد ونرد عليك.');
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('بلّغ عن ضرر')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Muted('اوصف الضرر وضيف صور. البلاغ بيتقبل في خلال المدة المكتوبة في الشروط من خلاص الغسلة.'),
        const SizedBox(height: 12),
        TextField(controller: _text, maxLines: 5, decoration: const InputDecoration(labelText: 'إيه اللي حصل؟'),
            onChanged: (_) => setState(() {})),
        const SizedBox(height: 12),
        OutlinedButton.icon(onPressed: _addPhoto, icon: const Icon(Icons.add_a_photo_outlined),
            label: Text(_photos.isEmpty ? 'ضيف صور' : '${_photos.length} صورة. ضيف كمان')),
        const SizedBox(height: 20),
        BusyButton(label: 'ابعت البلاغ', onPressed: _text.text.trim().isEmpty ? null : _send),
      ]),
    );
  }
}
