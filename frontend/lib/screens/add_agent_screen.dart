import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/classifier_form.dart';
import '../widgets/config_form.dart';
import '../widgets/mail_scheduler_form.dart';

/// 템플릿 선택 → 설정 입력 → 생성('구성 중…' 은 목록의 상태로 표시).
class AddAgentScreen extends ConsumerStatefulWidget {
  const AddAgentScreen({super.key});
  @override
  ConsumerState<AddAgentScreen> createState() => _AddAgentScreenState();
}

class _AddAgentScreenState extends ConsumerState<AddAgentScreen> {
  TemplateInfo? _template;
  List<ConfigFieldInfo> _schema = [];
  final _nameController = TextEditingController();
  Map<String, dynamic> _config = {};
  Map<String, dynamic> _secrets = {};
  bool _busy = false;

  Future<void> _pick(TemplateInfo t) async {
    final schema = await ref.read(apiProvider).configSchema(t.key);
    setState(() {
      _template = t;
      _schema = schema;
      _nameController.text = t.name;
    });
  }

  Future<void> _create() async {
    await _createWith(_nameController.text.trim(), _config, _secrets);
  }

  Future<void> _createWith(String name, Map<String, dynamic> config, Map<String, dynamic> secrets) async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).createAgent(_template!.key, name, config, secrets);
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('생성 실패: $e')));
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_template == null ? '템플릿 선택' : '에이전트 설정')),
      body: _template == null ? _templatePicker() : _configStep(),
    );
  }

  Widget _templatePicker() {
    final templatesAsync = ref.watch(templatesProvider);
    return templatesAsync.when(
      data: (templates) => SingleChildScrollView(
        padding: const EdgeInsets.all(28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('어떤 에이전트를 만들까요?',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: -0.5)),
            const SizedBox(height: 4),
            const Text('템플릿을 선택하면 설정 단계로 넘어갑니다',
                style: TextStyle(color: AppColors.muted)),
            const SizedBox(height: 24),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [for (final t in templates) _templateCard(t)],
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
    );
  }

  Widget _templateCard(TemplateInfo t) {
    final icon = t.viewType == 'kanban' ? Icons.view_kanban_rounded : Icons.schedule_send_rounded;
    return SizedBox(
      width: 300,
      height: 220,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => _pick(t),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: kBrandGradient,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: Colors.white, size: 28),
                ),
                const SizedBox(height: 16),
                Text(t.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, height: 1.2)),
                const SizedBox(height: 8),
                Expanded(
                  child: Text(t.description,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13, color: AppColors.muted, height: 1.4)),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text(t.viewType == 'kanban' ? '메일 수신형' : '스케줄형',
                        style: const TextStyle(
                            fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.primary)),
                    const Spacer(),
                    const Icon(Icons.arrow_forward_rounded, size: 18, color: AppColors.primary),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _configStep() {
    // 전용 폼: 메일 스케줄러(2단계 마법사) / 분류·요약
    if (_template!.key == 'mail_scheduler' || _template!.key == 'project_tracker') {
      final isSched = _template!.key == 'mail_scheduler';
      return SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: isSched
                ? MailSchedulerForm(
                    initialName: _template!.name,
                    initialConfig: const {},
                    wizard: true,
                    busy: _busy,
                    submitLabel: '생성',
                    onSubmit: (name, config) => _createWith(name, config, const {}),
                  )
                : ClassifierForm(
                    initialName: _template!.name,
                    initialConfig: const {},
                    busy: _busy,
                    submitLabel: '생성',
                    onSubmit: (name, config) => _createWith(name, config, const {}),
                  ),
          ),
        ),
      );
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: '에이전트 이름', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            ConfigForm(
              fields: _schema,
              onChanged: (c, s) {
                _config = c;
                _secrets = s;
              },
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _create,
              child: _busy
                  ? const Text('에이전트 구성 중…')
                  : const Text('다음 (생성)'),
            ),
          ],
        ),
      ),
    );
  }
}
