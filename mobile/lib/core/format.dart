/// Money is integer piastres everywhere; shown in whole pounds.
String money(num piastres) {
  final pounds = piastres / 100;
  final text = pounds == pounds.roundToDouble()
      ? pounds.toInt().toString()
      : pounds.toStringAsFixed(2);
  return '$text ج.م';
}

const _days = {
  DateTime.saturday: 'السبت',
  DateTime.sunday: 'الحد',
  DateTime.monday: 'الاتنين',
  DateTime.tuesday: 'التلات',
  DateTime.wednesday: 'الأربع',
  DateTime.thursday: 'الخميس',
  DateTime.friday: 'الجمعة',
};

/// Server times are in Cairo time; the app shows them in the phone's local time
/// (Egypt). For testing in another time zone we convert with the offset sent.
DateTime parseServerTime(String iso) => DateTime.parse(iso).toLocal();

String dayName(DateTime d) => _days[d.weekday]!;

String shortDate(DateTime d) => '${d.day}/${d.month}';

/// 3:30 م
String clock(DateTime d) {
  final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
  final m = d.minute.toString().padLeft(2, '0');
  return '$h:$m ${d.hour < 12 ? 'ص' : 'م'}';
}

String dayLabel(DateTime d, {DateTime? today}) {
  final t = today ?? DateTime.now();
  final a = DateTime(d.year, d.month, d.day);
  final b = DateTime(t.year, t.month, t.day);
  final diff = a.difference(b).inDays;
  if (diff == 0) return 'النهارده';
  if (diff == 1) return 'بكرة';
  return dayName(d);
}

String fullWhen(DateTime d) =>
    '${dayLabel(d)} ${shortDate(d)} الساعة ${clock(d)}';

/// 45 → "45 دقيقة", 105 → "ساعة و 45 دقيقة" (space after و so the number is not
/// glued to an Arabic letter, which scrambles the order on screen).
String duration(int minutes) {
  final h = minutes ~/ 60, m = minutes % 60;
  final hours = h == 0
      ? ''
      : (h == 1 ? 'ساعة' : (h == 2 ? 'ساعتين' : '$h ساعات'));
  if (m == 0) return hours;
  if (h == 0) return '$m دقيقة';
  return '$hours و $m دقيقة';
}

/// "كود BAREEQ20" for a coupon, else the kind's name (كارت الغسيل، ...).
String extraDiscountTitle(Map o) => o['extra_discount_kind'] == 'coupon'
    ? 'كود ${o['coupon_code']}'
    : '${o['extra_discount_label']}';
