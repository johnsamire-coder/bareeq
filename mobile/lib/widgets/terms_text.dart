import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Shows the terms text (simple Markdown: # headings, - bullets, **bold**).
class TermsText extends StatelessWidget {
  const TermsText(this.text, {super.key});
  final String text;

  List<TextSpan> _inline(String line, TextStyle base) {
    final spans = <TextSpan>[];
    final parts = line.split('**');
    for (var i = 0; i < parts.length; i++) {
      spans.add(
        TextSpan(
          text: parts[i],
          style: i.isOdd ? base.copyWith(fontWeight: FontWeight.w700) : base,
        ),
      );
    }
    return spans;
  }

  @override
  Widget build(BuildContext context) {
    const body = TextStyle(
      fontFamily: 'Cairo',
      fontSize: 14,
      height: 1.7,
      color: BrandColors.layl,
    );
    final children = <Widget>[];
    for (final raw in text.split('\n')) {
      final line = raw.trimRight();
      if (line.isEmpty) continue;
      if (line.startsWith('# ')) {
        children.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              line.substring(2),
              style: body.copyWith(fontSize: 19, fontWeight: FontWeight.w700),
            ),
          ),
        );
      } else if (line.startsWith('## ')) {
        children.add(
          Padding(
            padding: const EdgeInsets.only(top: 14, bottom: 4),
            child: Text(
              line.substring(3),
              style: body.copyWith(fontSize: 16, fontWeight: FontWeight.w700),
            ),
          ),
        );
      } else if (line.startsWith('- ')) {
        children.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.only(top: 9, left: 8),
                  child: CircleAvatar(
                    radius: 2.5,
                    backgroundColor: BrandColors.mayya,
                  ),
                ),
                Expanded(
                  child: Text.rich(
                    TextSpan(children: _inline(line.substring(2), body)),
                  ),
                ),
              ],
            ),
          ),
        );
      } else {
        children.add(Text.rich(TextSpan(children: _inline(line, body))));
      }
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: children,
    );
  }
}
