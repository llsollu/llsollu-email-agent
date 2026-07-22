import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../widgets/config_form.dart';

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
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).createAgent(
            _template!.key, _nameController.text.trim(), _config, _secrets);
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
      data: (templates) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final t in templates)
            Card(
              child: ListTile(
                leading: Icon(t.viewType == 'kanban' ? Icons.view_kanban : Icons.schedule_send),
                title: Text(t.name),
                subtitle: Text(t.description),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _pick(t),
              ),
            ),
        ],
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
    );
  }

  Widget _configStep() {
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
