import 'package:bareeq/widgets/terms_text.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('terms text shows headings, bullets and bold', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: TermsText('# شروط بريق\n## الإلغاء\n- ببلاش لحد **ساعتين** قبل الميعاد.')),
    ));
    expect(find.text('شروط بريق'), findsOneWidget);
    expect(find.text('الإلغاء'), findsOneWidget);
    expect(find.textContaining('ساعتين', findRichText: true), findsOneWidget);
  });
}
