import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show FontLoader;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'state/providers.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Pretendard 를 CDN(jsDelivr)에서 런타임 로드해 엔진에 등록.
  // CanvasKit 은 CSS @font-face 를 캔버스 텍스트에 적용하지 않으므로 FontLoader 로 등록한다.
  // 실패해도(오프라인 등) 시스템 폰트로 자연 폴백. 비동기라 앱 시작을 막지 않음.
  _loadPretendard();
  runApp(const ProviderScope(child: LlsolluApp()));
}

Future<void> _loadPretendard() async {
  const base = 'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static';
  const files = [
    'Pretendard-Regular.otf',
    'Pretendard-Medium.otf',
    'Pretendard-SemiBold.otf',
    'Pretendard-Bold.otf',
    'Pretendard-ExtraBold.otf',
  ];
  final dio = Dio();
  final loader = FontLoader('Pretendard');
  for (final f in files) {
    loader.addFont(
      dio
          .get<List<int>>('$base/$f', options: Options(responseType: ResponseType.bytes))
          .then((r) => ByteData.view(Uint8List.fromList(r.data!).buffer)),
    );
  }
  try {
    await loader.load();
  } catch (_) {
    // 폰트 로드 실패 시 시스템 폰트 사용
  }
}

class LlsolluApp extends ConsumerWidget {
  const LlsolluApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'LLSOLLU Email Agent',
      theme: buildAppTheme(),
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
