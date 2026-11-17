import 'package:flutter/material.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import 'crud.dart';

Future<List<(Object, String)>> serviceOptions(Api api) async => [
  for (final s in await api.get('manage/services/') as List)
    (s['id'] as Object, '${s['name']}'),
];

Future<List<(Object, String)>> zoneOptions(Api api) async => [
  for (final z in await api.get('zones/') as List)
    (z['id'] as Object, '${z['name']}'),
];

Widget servicesScreen() => CrudScreen(
  title: 'الخدمات',
  endpoint: 'manage/services/',
  canAdd: false,
  note: 'الأسعار والمدد ليهم صفحات لوحدهم.',
  itemTitle: (r) => '${r['name']}',
  itemSubtitle: (r) => [
    if (r['needs_shade'] == true) 'محتاجة ضل',
    if ((r['replaces'] as List).isNotEmpty) 'بتلغي خدمات تانية',
  ].join(' • '),
  fields: [
    const FieldSpec('name', 'الاسم', FieldType.text, required: true),
    const FieldSpec('description', 'الوصف', FieldType.multiline),
    const FieldSpec('is_active', 'ظاهرة للعملاء', FieldType.boolean),
    const FieldSpec(
      'needs_shade',
      'محتاجة ضل (تنبيه لو العربية في الشارع)',
      FieldType.boolean,
    ),
    FieldSpec(
      'replaces',
      'لو العميل اختارها، بتلغي الخدمات دي',
      FieldType.multi,
      options: serviceOptions,
    ),
  ],
);

Widget bundlesScreen() => CrudScreen(
  title: 'الباقات',
  endpoint: 'manage/bundles/',
  itemTitle: (r) => '${r['name']} • خصم ${r['discount_percent']}%',
  itemSubtitle: (r) => '${r['description']}',
  newDefaults: const {'is_active': true, 'services': []},
  fields: [
    const FieldSpec('name', 'الاسم', FieldType.text, required: true),
    const FieldSpec('description', 'الوصف', FieldType.text),
    FieldSpec(
      'services',
      'الخدمات اللي في الباقة (2 على الأقل)',
      FieldType.multi,
      options: serviceOptions,
    ),
    const FieldSpec(
      'discount_percent',
      'الخصم %',
      FieldType.integer,
      required: true,
    ),
    const FieldSpec('sort_order', 'الترتيب', FieldType.integer),
    const FieldSpec('is_active', 'شغالة', FieldType.boolean),
  ],
);

Widget oilTypesScreen() => CrudScreen(
  title: 'أنواع الزيت',
  endpoint: 'manage/oil-types/',
  note: 'الشركة بتبيع الزيت بسعر التكلفة، وبيظهر للعميل في سطر لوحده.',
  itemTitle: (r) => '${r['name']} • ${money(r['price'])}',
  itemSubtitle: (r) => '${r['description']}',
  newDefaults: const {'is_active': true},
  fields: const [
    FieldSpec('name', 'نوع الزيت', FieldType.text, required: true),
    FieldSpec('description', 'الوصف (اللزوجة، الكمية...)', FieldType.text),
    FieldSpec('price', 'السعر', FieldType.money, required: true),
    FieldSpec('is_active', 'متاح', FieldType.boolean),
  ],
);

Widget materialsScreen() => CrudScreen(
  title: 'الخامات',
  endpoint: 'manage/materials/',
  note: 'الفني بيكتب الكمية بس، والتكلفة بتتحسب بسعر الوحدة يومها.',
  itemTitle: (r) => '${r['name']}',
  itemSubtitle: (r) => '${money(r['unit_cost'])} لكل ${r['unit_label']}',
  newDefaults: const {'is_active': true, 'unit': 'liter'},
  fields: [
    const FieldSpec('name', 'الخامة', FieldType.text, required: true),
    FieldSpec(
      'unit',
      'الوحدة',
      FieldType.choice,
      required: true,
      options: (_) async => const [
        ('liter', 'لتر'),
        ('box', 'علبة'),
        ('piece', 'قطعة'),
      ],
    ),
    const FieldSpec('unit_cost', 'سعر الوحدة', FieldType.money, required: true),
    const FieldSpec('is_active', 'مستخدمة', FieldType.boolean),
  ],
);

Widget couponsScreen() => CrudScreen(
  title: 'الكوبونات',
  endpoint: 'manage/coupons/',
  note:
      'العميل بيكتب الكود في شاشة الدفع. الخصم على الخدمات بس (مش الزيت)، والمطلوب بيطلع جنيهات صحيحة.',
  itemTitle: (r) =>
      '${r['code']} • ${r['kind'] == 'percent' ? '${r['value']}%' : money(r['value'])}',
  itemSubtitle: (r) =>
      'استُخدم ${r['times_used']}${r['max_uses_total'] == null ? '' : ' من ${r['max_uses_total']}'}'
      ' • ينتهي ${shortDate(parseServerTime('${r['expires_at']}'))}${r['zone_name'] == null ? '' : ' • ${r['zone_name']}'}',
  newDefaults: const {
    'kind': 'percent',
    'is_active': true,
    'max_uses_per_customer': 1,
  },
  // The amount is typed in pounds; the server keeps piastres.
  toForm: (r) => {
    ...r,
    'value': r['kind'] == 'amount' ? (r['value'] as int) ~/ 100 : r['value'],
  },
  toPayload: (b) => {
    ...b,
    'value': b['kind'] == 'amount'
        ? ((b['value'] ?? 0) as int) * 100
        : b['value'],
  },
  fields: [
    const FieldSpec(
      'code',
      'الكود',
      FieldType.text,
      required: true,
      help: 'مثلاً BAREEQ20 (حروف إنجليزي وأرقام).',
    ),
    FieldSpec(
      'kind',
      'النوع',
      FieldType.choice,
      required: true,
      options: (_) async => const [
        ('percent', 'نسبة %'),
        ('amount', 'مبلغ ثابت'),
      ],
    ),
    const FieldSpec(
      'value',
      'القيمة',
      FieldType.integer,
      required: true,
      help: 'نسبة من 1 لـ 100، أو مبلغ بالجنيه.',
    ),
    const FieldSpec('expires_at', 'ينتهي يوم', FieldType.date, required: true),
    const FieldSpec(
      'max_uses_total',
      'أقصى عدد مرات لكل الناس',
      FieldType.integer,
      help: 'فاضي = من غير حد',
    ),
    const FieldSpec(
      'max_uses_per_customer',
      'أقصى عدد مرات لكل عميل',
      FieldType.integer,
      required: true,
    ),
    FieldSpec(
      'zone',
      'منطقة معينة (اختياري)',
      FieldType.choice,
      options: zoneOptions,
    ),
    const FieldSpec('is_active', 'شغال', FieldType.boolean),
  ],
);

Widget heardAboutScreen() => CrudScreen(
  title: '«عرفتنا منين»',
  endpoint: 'manage/heard-about-options/',
  itemTitle: (r) => '${r['label']}',
  newDefaults: const {'is_active': true, 'sort_order': 0},
  fields: const [
    FieldSpec('label', 'الاختيار', FieldType.text, required: true),
    FieldSpec('sort_order', 'الترتيب', FieldType.integer),
    FieldSpec('is_active', 'ظاهر', FieldType.boolean),
  ],
);

Widget ratingTagsScreen() => CrudScreen(
  title: 'كلمات التقييم السريعة',
  endpoint: 'manage/rating-tags/',
  itemTitle: (r) => '${r['name']}',
  newDefaults: const {'is_active': true, 'sort_order': 0},
  fields: const [
    FieldSpec('name', 'الكلمة', FieldType.text, required: true),
    FieldSpec('sort_order', 'الترتيب', FieldType.integer),
    FieldSpec('is_active', 'ظاهرة', FieldType.boolean),
  ],
);
