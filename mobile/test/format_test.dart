import 'package:bareeq/core/format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('money shows whole pounds', () {
    expect(money(24300), '243 ج.م');
    expect(money(0), '0 ج.م');
    expect(money(16250), '162.50 ج.م');
  });

  test('clock is 12-hour with morning/evening', () {
    expect(clock(DateTime(2026, 11, 18, 9, 0)), '9:00 ص');
    expect(clock(DateTime(2026, 11, 18, 14, 30)), '2:30 م');
    expect(clock(DateTime(2026, 11, 18, 0, 5)), '12:05 ص');
    expect(clock(DateTime(2026, 11, 18, 12, 0)), '12:00 م');
  });

  test('durations in Egyptian Arabic', () {
    expect(duration(45), '45 دقيقة');
    expect(duration(60), 'ساعة');
    expect(duration(105), 'ساعة و 45 دقيقة');
    expect(duration(120), 'ساعتين');
    expect(duration(180), '3 ساعات');
    expect(duration(210), '3 ساعات و 30 دقيقة');
  });

  test('day labels', () {
    final today = DateTime(2026, 11, 17); // Tuesday
    expect(dayLabel(DateTime(2026, 11, 17, 10), today: today), 'النهارده');
    expect(dayLabel(DateTime(2026, 11, 18), today: today), 'بكرة');
    expect(dayLabel(DateTime(2026, 11, 20), today: today), 'الجمعة');
    expect(dayLabel(DateTime(2026, 11, 21), today: today), 'السبت');
  });
}
