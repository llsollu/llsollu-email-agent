import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import 'config_form.dart';

/// ⚙️ 설정: 생성 시 설정을 열람·수정. 모든 뷰 공용.
/// 저장 시 true 반환.
Future<bool?> showAgentSettings(BuildContext context, WidgetRef ref, AgentInfo agent) {
  return showDialog<bool>(
    context: context,
    builder: (_) => _SettingsDialog(agent: agent),
  );
}

class _SettingsDialog extends ConsumerStatefulWidget {
  final AgentInfo agent;
  const _SettingsDialog({required this.agent});
  @override
  ConsumerState<_SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends ConsumerState<_SettingsDialog> {
  List<ConfigFieldInfo>? _schema;
  final _nameController = TextEditingController();
  Map<String, dynamic> _config = {};
  Map<String, dynamic> _secrets = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _nameController.text = widget.agent.name;
    _load();
  }

  Future<void> _load() async {
    final schema = await ref.read(apiProvider).configSchema(widget.agent.templateKey);
    setState(() => _schema = schema);
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).updateAgent(
            widget.agent.id,
            name: _nameController.text.trim(),
            config: _config,
            secrets: _secrets,
          );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('저장 실패: $e')));
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('삭제'),
        content: Text('"${widget.agent.name}" 을(를) 삭제할까요?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('삭제')),
        ],
      ),
    );
    if (ok == true) {
      await ref.read(apiProvider).deleteAgent(widget.agent.id);
      if (mounted) Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.settings),
          const SizedBox(width: 8),
          const Expanded(child: Text('에이전트 설정')),
          IconButton(
            tooltip: '삭제',
            icon: const Icon(Icons.delete_outline),
            onPressed: _busy ? null : _delete,
          ),
        ],
      ),
      content: SizedBox(
        width: 480,
        child: _schema == null
            ? const SizedBox(height: 120, child: Center(child: CircularProgressIndicator()))
            : SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: _nameController,
                      decoration: const InputDecoration(labelText: '이름', border: OutlineInputBorder()),
                    ),
                    ConfigForm(
                      fields: _schema!,
                      initialConfig: widget.agent.config,
                      onChanged: (c, s) {
                        _config = c;
                        _secrets = s;
                      },
                    ),
                  ],
                ),
              ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('취소')),
        FilledButton(onPressed: _busy ? null : _save, child: const Text('저장')),
      ],
    );
  }
}
