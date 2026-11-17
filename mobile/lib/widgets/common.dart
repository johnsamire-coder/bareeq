import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../core/api.dart';
import '../core/theme.dart';

void showError(BuildContext context, Object e) {
  final msg = e is ApiError ? e.message : 'حصلت مشكلة. جرب تاني.';
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg), backgroundColor: BrandColors.danger));
}

void showInfo(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg), backgroundColor: BrandColors.layl));
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});
  final String text;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 10),
        child: Row(children: [
          Expanded(child: Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700))),
          ?trailing,
        ]),
      );
}

class Muted extends StatelessWidget {
  const Muted(this.text, {super.key, this.size = 13, this.align});
  final String text;
  final double size;
  final TextAlign? align;

  @override
  Widget build(BuildContext context) =>
      Text(text, textAlign: align, style: TextStyle(fontSize: size, color: BrandColors.muted));
}

class Loading extends StatelessWidget {
  const Loading({super.key});

  @override
  Widget build(BuildContext context) =>
      const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()));
}

class ErrorRetry extends StatelessWidget {
  const ErrorRetry({super.key, required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.wifi_off_rounded, size: 40, color: BrandColors.muted),
            const SizedBox(height: 8),
            Text(error is ApiError ? (error as ApiError).message : 'حصلت مشكلة.', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: const Text('جرب تاني')),
          ]),
        ),
      );
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.text, this.action});
  final IconData icon;
  final String text;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
        child: Column(children: [
          Icon(icon, size: 44, color: BrandColors.mayya),
          const SizedBox(height: 10),
          Text(text, textAlign: TextAlign.center, style: const TextStyle(color: BrandColors.muted)),
          if (action != null) ...[const SizedBox(height: 16), action!],
        ]),
      );
}

/// Button that shows a spinner while its async action runs.
class BusyButton extends StatefulWidget {
  const BusyButton({super.key, required this.label, required this.onPressed, this.outlined = false, this.icon});
  final String label;
  final Future<void> Function()? onPressed;
  final bool outlined;
  final IconData? icon;

  @override
  State<BusyButton> createState() => _BusyButtonState();
}

class _BusyButtonState extends State<BusyButton> {
  bool _busy = false;

  Future<void> _run() async {
    setState(() => _busy = true);
    try {
      await widget.onPressed!();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final onPressed = (widget.onPressed == null || _busy) ? null : _run;
    final child = _busy
        ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
        : Row(mainAxisSize: MainAxisSize.min, children: [
            if (widget.icon != null) ...[Icon(widget.icon, size: 20), const SizedBox(width: 8)],
            Text(widget.label),
          ]);
    return widget.outlined
        ? OutlinedButton(onPressed: onPressed, child: child)
        : FilledButton(onPressed: onPressed, child: child);
  }
}

/// Service icon from the brand kit, by service code.
class ServiceIcon extends StatelessWidget {
  const ServiceIcon(this.code, {super.key, this.size = 36});
  final String code;
  final double size;

  static const _files = {
    'exterior-wash': 'wash-exterior',
    'interior-wash': 'wash-interior',
    'engine-wash': 'engine',
    'exterior-detailing': 'detail-exterior',
    'interior-detailing': 'detail-interior',
    'polish-protection': 'polish',
    'headlight-restoration': 'headlights',
    'oil-change': 'oil',
  };

  @override
  Widget build(BuildContext context) {
    final f = _files[code];
    if (f == null) return Icon(Icons.local_car_wash, size: size, color: BrandColors.layl);
    return SvgPicture.asset('assets/icons/$f.svg', width: size, height: size);
  }
}

class Pill extends StatelessWidget {
  const Pill(this.text, {super.key, this.color = BrandColors.razaz, this.textColor = BrandColors.layl});
  final String text;
  final Color color;
  final Color textColor;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: textColor)),
      );
}

/// Label on one side, value on the other (invoice lines).
class KeyValue extends StatelessWidget {
  const KeyValue(this.label, this.value, {super.key, this.bold = false, this.color});
  final String label;
  final String value;
  final bool bold;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(fontWeight: bold ? FontWeight.w700 : FontWeight.w400, fontSize: bold ? 16 : 14, color: color);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [Expanded(child: Text(label, style: style)), Text(value, style: style)]),
    );
  }
}

Future<bool> confirmDialog(BuildContext context, String title, String body, {String yes = 'أيوه', String no = 'لأ'}) async {
  final r = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      title: Text(title),
      content: Text(body),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(no)),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(yes)),
      ],
    ),
  );
  return r == true;
}

/// Asks for a short text (a reason, a note). Returns null when cancelled.
Future<String?> askText(BuildContext context, String title, {String hint = '', String ok = 'تمام', bool required = true}) async {
  final c = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (d) => StatefulBuilder(
      builder: (d, set) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, autofocus: true, maxLines: 3, decoration: InputDecoration(hintText: hint),
            onChanged: (_) => set(() {})),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d), child: const Text('رجوع')),
          FilledButton(onPressed: required && c.text.trim().isEmpty ? null : () => Navigator.pop(d, c.text.trim()), child: Text(ok)),
        ],
      ),
    ),
  );
}

/// A protected image (InstaPay screenshot, rating/damage photo) by server path.
class ServerImage extends StatelessWidget {
  const ServerImage(this.path, {super.key, required this.loader, this.height = 160});
  final String path;
  final Future<dynamic> Function(String) loader;
  final double height;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: height,
        child: FutureBuilder(
          future: loader(path),
          builder: (_, snap) => snap.hasData
              ? GestureDetector(
                  onTap: () => showDialog(context: context, builder: (_) => Dialog(child: InteractiveViewer(child: Image.memory(snap.data)))),
                  child: ClipRRect(borderRadius: BorderRadius.circular(10), child: Image.memory(snap.data, fit: BoxFit.cover, width: double.infinity)),
                )
              : Container(decoration: BoxDecoration(color: BrandColors.razaz, borderRadius: BorderRadius.circular(10))),
        ),
      );
}
