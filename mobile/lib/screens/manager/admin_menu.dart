import 'package:flutter/material.dart';

import '../../widgets/common.dart';
import 'cars_catalog_screen.dart';
import 'close_day_screen.dart';
import 'custody_screen.dart';
import 'live_map_screen.dart';
import 'supervisors_screen.dart';
import 'subscriptions_admin_screen.dart';
import 'wallet_report_screen.dart';
import 'customers_screen.dart';
import 'reports_screen.dart';
import 'lists.dart';
import 'pricing_screens.dart';
import 'settings_screens.dart';
import 'technicians_screen.dart';
import 'zones_screen.dart';

/// Everything the manager manages (there is no web dashboard).
class AdminMenu extends StatelessWidget {
  const AdminMenu({super.key});

  @override
  Widget build(BuildContext context) {
    Widget item(
      IconData icon,
      String title,
      String sub,
      Widget Function() page,
    ) => Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(sub),
        trailing: const Icon(Icons.chevron_left),
        onTap: () =>
            Navigator.push(context, MaterialPageRoute(builder: (_) => page())),
      ),
    );
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const SectionTitle('العملاء والأرقام'),
        item(
          Icons.query_stats,
          'التقارير',
          'الإيراد واللي اتحصّل والهامش والعملاء والمدد',
          () => const ReportsScreen(),
        ),
        item(
          Icons.people_outline,
          'العملاء',
          'ملف كل عميل، المحفظة، الرسوم، الملاحظات',
          () => const CustomersScreen(),
        ),
        item(
          Icons.event_repeat,
          'الاشتراكات',
          'المشتركين، وإيراد الاشتراكات كل شهر',
          () => const SubscriptionsAdminScreen(),
        ),
        item(
          Icons.savings_outlined,
          'تقرير المحفظة',
          'الرصيد المفتوح على الشركة، واللي نزل واتصرف وانتهى',
          () => const WalletReportScreen(),
        ),
        item(
          Icons.account_balance_wallet_outlined,
          'عهدة الفنيين',
          'العجز والزيادة في التقفيل، واللي على كل فني',
          () => const CustodyScreen(),
        ),
        const SectionTitle('الشغل'),
        item(
          Icons.map_outlined,
          'خريطة اليوم',
          'الفنيين وهم في الطريق، وطلبات النهارده',
          () => const LiveMapScreen(),
        ),
        item(
          Icons.supervisor_account_outlined,
          'المشرفين',
          'إضافة، والمناطق، والإيقاف',
          () => const SupervisorsScreen(),
        ),
        item(
          Icons.engineering_outlined,
          'الفنيين',
          'إضافة، إيقاف، المناطق، المواعيد، الإجازات',
          () => const TechniciansScreen(),
        ),
        item(
          Icons.map_outlined,
          'المناطق',
          'رسم الحدود على الخريطة، فتح وقفل',
          () => const ZonesScreen(),
        ),
        item(
          Icons.notifications_active_outlined,
          'طلبات «بلغوني»',
          'أماكن عايزة الخدمة ولسه مش عندنا',
          () => const DemandScreen(),
        ),
        item(
          Icons.thunderstorm_outlined,
          'قفل يوم (الجو)',
          'إلغاء حجوزات يوم لمنطقة أو للكل',
          () => const CloseDayScreen(),
        ),
        const SectionTitle('الأسعار والخدمات'),
        item(
          Icons.sell_outlined,
          'الأسعار',
          'كل خدمة لكل منطقة وحجم',
          () => const PricesScreen(),
        ),
        item(
          Icons.timer_outlined,
          'المدد',
          'كل خدمة لكل حجم',
          () => const DurationsScreen(),
        ),
        item(
          Icons.local_car_wash_outlined,
          'الخدمات',
          'الأسماء، الضل، مين بيلغي مين',
          servicesScreen,
        ),
        item(
          Icons.event_repeat,
          'باقات الاشتراك',
          'عدد الغسلات، والخدمات، ونسبة الخصم',
          subscriptionPlansScreen,
        ),
        item(
          Icons.workspaces_outline,
          'الباقات',
          'الخدمات والخصم',
          bundlesScreen,
        ),
        item(
          Icons.confirmation_number_outlined,
          'الكوبونات',
          'أكواد الخصم',
          couponsScreen,
        ),
        item(
          Icons.oil_barrel_outlined,
          'أنواع الزيت',
          'الأسماء والأسعار',
          oilTypesScreen,
        ),
        item(
          Icons.inventory_2_outlined,
          'الخامات',
          'الوحدة وسعر الوحدة',
          materialsScreen,
        ),
        const SectionTitle('الإعدادات'),
        item(
          Icons.tune,
          'جدول الإعدادات',
          'كل أرقام الشغل',
          () => const SettingsScreen(),
        ),
        item(
          Icons.description_outlined,
          'الشروط والأحكام',
          'النسخ ونشر نسخة جديدة',
          () => const TermsManageScreen(),
        ),
        item(
          Icons.list_alt,
          '«عرفتنا منين»',
          'اختيارات التسجيل',
          heardAboutScreen,
        ),
        item(
          Icons.star_outline,
          'كلمات التقييم',
          'الكلمات السريعة',
          ratingTagsScreen,
        ),
        const SectionTitle('العربيات'),
        item(
          Icons.directions_car_outlined,
          'الماركات والموديلات',
          'الحجم بيحدد السعر والمدة',
          () => const CarsCatalogScreen(),
        ),
        item(
          Icons.rate_review_outlined,
          'موديلات محتاجة مراجعة',
          '«موديلي مش موجود»',
          () => const UnlistedCarsScreen(),
        ),
      ],
    );
  }
}
