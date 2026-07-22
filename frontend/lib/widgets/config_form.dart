import 'package:flutter/material.dart';

import '../models/models.dart';

/// config_schema 기반 동적 폼. 생성 마법사와 ⚙️ 설정 편집에서 공용.
class ConfigForm extends StatefulWidget {
  final List<ConfigFieldInfo> fields;
  final Map<String, dynamic> initialConfig;

  /// (config, secrets) 를 반환. secret 필드는 secrets 로 분리.
  final void Function(Map<String, dynamic> config, Map<String, dynamic> secrets) onChanged;

  const ConfigForm({
    super.key,
    required this.fields,
    required this.onChanged,
    this.initialConfig = const {},
  });

  @override
  State<ConfigForm> createState() => _ConfigFormState();
}

class _ConfigFormState extends State<ConfigForm> {
  final Map<String, TextEditingController> _controllers = {};
  final Map<String, bool> _bools = {};

  @override
  void initState() {
    super.initState();
    for (final f in widget.fields) {
      if (f.type == 'bool') {
        _bools[f.key] = (widget.initialConfig[f.key] ?? f.defaultValue ?? false) == true;
      } else {
        final v = widget.initialConfig[f.key] ?? (f.secret ? '' : (f.defaultValue ?? ''));
        _controllers[f.key] = TextEditingController(text: '$v');
      }
    }
  }

  void _emit() {
    final config = <String, dynamic>{};
    final secrets = <String, dynamic>{};
    for (final f in widget.fields) {
      if (f.type == 'bool') {
        config[f.key] = _bools[f.key] ?? false;
      } else {
        final text = _controllers[f.key]!.text.trim();
        if (f.secret) {
          if (text.isNotEmpty) secrets[f.key] = text; // 미입력 시 기존값 유지
        } else {
          config[f.key] = f.type == 'int' ? int.tryParse(text) : text;
        }
      }
    }
    widget.onChanged(config, secrets);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final f in widget.fields) ...[
          if (f.type == 'bool')
            SwitchListTile(
              title: Text(f.label),
              subtitle: f.help != null ? Text(f.help!) : null,
              value: _bools[f.key] ?? false,
              onChanged: (v) {
                setState(() => _bools[f.key] = v);
                _emit();
              },
            )
          else
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: TextField(
                controller: _controllers[f.key],
                obscureText: f.secret,
                maxLines: f.type == 'text' ? 3 : 1,
                decoration: InputDecoration(
                  labelText: f.label + (f.required ? ' *' : ''),
                  helperText: f.secret ? (f.help ?? '변경 시에만 입력') : f.help,
                  border: const OutlineInputBorder(),
                ),
                onChanged: (_) => _emit(),
              ),
            ),
        ],
      ],
    );
  }
}
