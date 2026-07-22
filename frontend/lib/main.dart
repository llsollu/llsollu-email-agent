import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'state/providers.dart';

void main() {
  runApp(const ProviderScope(child: LlsolluApp()));
}

class LlsolluApp extends ConsumerWidget {
  const LlsolluApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'LLSOLLU Email Agent',
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF2D6CDF),
        useMaterial3: true,
      ),
      debugShowCheckedModeBanner: false,
      home: const _AuthGate(),
    );
  }
}

/// 앱 시작 시 /me 로 세션 확인 → 자동 로그인. 실패 시 로그인 화면.
class _AuthGate extends ConsumerStatefulWidget {
  const _AuthGate();
  @override
  ConsumerState<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends ConsumerState<_AuthGate> {
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    try {
      final user = await ref.read(apiProvider).me();
      ref.read(currentUserProvider.notifier).state = user;
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final user = ref.watch(currentUserProvider);
    return user == null ? const LoginScreen() : const HomeScreen();
  }
}
