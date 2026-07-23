import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/animated_background.dart';

/// 첫 접속: 회사 이메일 + 비밀번호로 로그인.
/// - DB에 있는 계정: 비밀번호 일치 시 로그인
/// - 사내(Graph) 계정이나 미가입: 비밀번호 설정 창 → 가입 후 로그인
/// - 회사 계정이 아니면: 경고
/// '자동 로그인' 체크 시 세션이 장기 유지된다(기본 ON).
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _remember = true;
  bool _obscure = true;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    // 두 필드 입력 여부에 따라 버튼 활성화 갱신
    _email.addListener(() => setState(() {}));
    _password.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _email.text.trim().isNotEmpty && _password.text.isNotEmpty && !_busy;

  Future<void> _submit() async {
    if (!_canSubmit) return;
    final email = _email.text.trim().toLowerCase();
    final password = _password.text;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = ref.read(apiProvider);
      final status = await api.checkEmail(email);
      if (status == 'not_company') {
        setState(() => _error = '정확한 회사 메일주소를 입력하세요');
        return;
      }
      UserInfo user;
      if (status == 'needs_setup') {
        final setPw = await _askNewPassword(prefill: password);
        if (setPw == null) return; // 취소
        user = await api.register(email, setPw, _remember);
      } else {
        // existing
        user = await api.login(email, password, _remember);
      }
      ref.read(currentUserProvider.notifier).state = user;
    } catch (e) {
      setState(() => _error = _clean('$e'));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _clean(String e) => e.replaceFirst('Exception: ', '');

  /// 사내 계정 최초 로그인: 비밀번호 설정 창.
  Future<String?> _askNewPassword({required String prefill}) {
    final pw = TextEditingController(text: prefill);
    final pw2 = TextEditingController();
    String? err;
    bool obscure = true;
    return showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) {
          void confirm() {
            if (pw.text.length < 4) {
              setLocal(() => err = '비밀번호는 4자 이상이어야 합니다');
              return;
            }
            if (pw.text != pw2.text) {
              setLocal(() => err = '비밀번호가 일치하지 않습니다');
              return;
            }
            Navigator.of(ctx).pop(pw.text);
          }

          return AlertDialog(
            title: const Text('비밀번호 설정'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('사내 계정이 확인되었습니다.\n사용할 비밀번호를 설정하세요.'),
                const SizedBox(height: 16),
                TextField(
                  controller: pw,
                  obscureText: obscure,
                  decoration: InputDecoration(
                    labelText: '비밀번호',
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(obscure ? Icons.visibility : Icons.visibility_off),
                      onPressed: () => setLocal(() => obscure = !obscure),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: pw2,
                  obscureText: obscure,
                  decoration: const InputDecoration(
                    labelText: '비밀번호 확인',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => confirm(),
                ),
                if (err != null) ...[
                  const SizedBox(height: 12),
                  Text(err!, style: const TextStyle(color: Colors.red)),
                ],
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('취소')),
              FilledButton(onPressed: confirm, child: const Text('설정하고 로그인')),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AnimatedBackground(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Card(
                elevation: 18,
                shadowColor: AppColors.primary.withValues(alpha: 0.18),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(32, 36, 32, 32),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            gradient: kBrandGradient,
                            borderRadius: BorderRadius.circular(18),
                            boxShadow: [
                              BoxShadow(
                                  color: AppColors.primary.withValues(alpha: 0.35),
                                  blurRadius: 18,
                                  offset: const Offset(0, 8)),
                            ],
                          ),
                          child: const Icon(Icons.hub_rounded, color: Colors.white, size: 32),
                        ),
                      ),
                      const SizedBox(height: 18),
                      const Text('LLSOLLU Email Agent',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              fontSize: 24, fontWeight: FontWeight.w800, letterSpacing: -0.5)),
                      const SizedBox(height: 6),
                      const Text('회사 이메일과 비밀번호로 로그인하세요',
                          textAlign: TextAlign.center, style: TextStyle(color: AppColors.muted)),
                      const SizedBox(height: 24),
                  TextField(
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.username],
                    decoration: const InputDecoration(
                      labelText: '회사 이메일',
                      hintText: 'name@llsollu.com',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _password,
                    obscureText: _obscure,
                    autofillHints: const [AutofillHints.password],
                    decoration: InputDecoration(
                      labelText: '비밀번호',
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                        onPressed: () => setState(() => _obscure = !_obscure),
                      ),
                    ),
                    onSubmitted: (_) => _submit(),
                  ),
                  const SizedBox(height: 4),
                  CheckboxListTile(
                    value: _remember,
                    onChanged: (v) => setState(() => _remember = v ?? true),
                    title: const Text('자동 로그인'),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 8),
                    Text(_error!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _canSubmit ? _submit : null,
                    child: _busy
                        ? const SizedBox(
                            height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('로그인'),
                  ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
