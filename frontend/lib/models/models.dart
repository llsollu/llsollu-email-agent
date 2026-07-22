class UserInfo {
  final String id;
  final String email;
  final String? displayName;
  UserInfo({required this.id, required this.email, this.displayName});
  factory UserInfo.fromJson(Map<String, dynamic> j) =>
      UserInfo(id: j['id'], email: j['email'], displayName: j['display_name']);
}

class TemplateInfo {
  final String key, name, version, description, triggerKind, viewType;
  TemplateInfo({
    required this.key,
    required this.name,
    required this.version,
    required this.description,
    required this.triggerKind,
    required this.viewType,
  });
  factory TemplateInfo.fromJson(Map<String, dynamic> j) => TemplateInfo(
        key: j['key'],
        name: j['name'],
        version: j['version'],
        description: j['description'],
        triggerKind: j['trigger_kind'],
        viewType: j['view_type'],
      );
}

class ConfigFieldInfo {
  final String key, label, type;
  final bool required, secret;
  final String? help;
  final List<String>? options;
  final Object? defaultValue;
  ConfigFieldInfo.fromJson(Map<String, dynamic> j)
      : key = j['key'],
        label = j['label'],
        type = j['type'],
        required = j['required'] ?? false,
        secret = j['secret'] ?? false,
        help = j['help'],
        options = (j['options'] as List?)?.cast<String>(),
        defaultValue = j['default'];
}

class AgentInfo {
  final String id, templateKey, name, status;
  final String? errorDetail, viewType;
  final Map<String, dynamic> config;
  AgentInfo.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        templateKey = j['template_key'],
        name = j['name'],
        status = j['status'],
        errorDetail = j['error_detail'],
        viewType = j['view_type'],
        config = Map<String, dynamic>.from(j['config'] ?? {});
}

class ProjectInfo {
  final String id, clientName, title, status;
  final String? phase, latestUpdate;
  final List<IssueInfo> issues;
  ProjectInfo.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        clientName = j['client_name'],
        title = j['title'],
        status = j['status'],
        phase = j['phase'],
        latestUpdate = j['latest_update'],
        issues = ((j['issues'] as List?) ?? [])
            .map((e) => IssueInfo.fromJson(e))
            .toList();
}

class IssueInfo {
  final String id, type, summary, severity, status;
  IssueInfo.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        type = j['type'],
        summary = j['summary'],
        severity = j['severity'],
        status = j['status'];
}

class RunInfo {
  final String id, triggerSource, status;
  final String? error;
  final Map<String, dynamic> stats;
  RunInfo.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        triggerSource = j['trigger_source'],
        status = j['status'],
        error = j['error'],
        stats = Map<String, dynamic>.from(j['stats'] ?? {});
}
