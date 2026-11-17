import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'core/api.dart';
import 'core/session.dart';
import 'core/theme.dart';
import 'screens/auth/terms_screen.dart';
import 'screens/home_screen.dart';
import 'screens/staff_placeholder.dart';
import 'screens/manager/manager_home.dart';
import 'screens/tech/tech_home.dart';

void main() {
  // For automated screen tests in a browser only (flutter build web --dart-define=SEMANTICS=true):
  // exposes buttons and texts to the test tool. Off in the real app.
  if (const bool.fromEnvironment('SEMANTICS')) {
    WidgetsFlutterBinding.ensureInitialized();
    SemanticsBinding.instance.ensureSemantics();
  }
  final session = Session(Api())..restore();
  runApp(
    ChangeNotifierProvider.value(value: session, child: const BareeqApp()),
  );
}

class BareeqApp extends StatelessWidget {
  const BareeqApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'بريق',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      // Arabic first, right to left everywhere.
      locale: const Locale('ar', 'EG'),
      supportedLocales: const [Locale('ar', 'EG')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) => DemoBanner(child: child!),
      home: const RootGate(),
    );
  }
}

/// Picks the first screen: login, new terms to accept, or the app for the role.
class RootGate extends StatelessWidget {
  const RootGate({super.key});

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (s.loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!s.loggedIn) return const TermsScreen();
    if (s.needsTerms) return const TermsScreen(reaccept: true);
    if (s.role == 'customer') return const HomeScreen();
    if (s.role == 'technician') return const TechHome();
    if (s.role == 'manager') return const ManagerHome();
    return const StaffPlaceholder(); // supervisor: phase 4
  }
}

/// A clear strip on top of every screen while the test mode is on.
class DemoBanner extends StatelessWidget {
  const DemoBanner({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (!context.watch<Session>().demoMode) return child;
    final top = MediaQuery.paddingOf(context).top;
    return Column(
      children: [
        Material(
          color: BrandColors.lamaa,
          child: Padding(
            padding: EdgeInsets.fromLTRB(8, top + 4, 8, 4),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.science_outlined, size: 18, color: BrandColors.layl),
                SizedBox(width: 6),
                Text(
                  'نسخة تجريبية',
                  style: TextStyle(
                    fontFamily: 'Cairo',
                    fontWeight: FontWeight.w800,
                    color: BrandColors.layl,
                  ),
                ),
              ],
            ),
          ),
        ),
        Expanded(
          child: MediaQuery.removePadding(
            context: context,
            removeTop: true,
            child: child,
          ),
        ),
      ],
    );
  }
}
