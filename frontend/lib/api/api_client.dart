import 'package:dio/dio.dart';

import '../config.dart';
import '../models/models.dart';

/// 백엔드 REST 클라이언트. 세션은 httpOnly 쿠키(Web) 또는 쿠키 저장(Desktop) 기반.
class ApiClient {
  final Dio _dio;

  ApiClient()
      : _dio = Dio(BaseOptions(
          baseUrl: apiRoot,
          // Desktop/macOS: 쿠키 유지를 위해 credentials 허용
          extra: {'withCredentials': true},
          validateStatus: (s) => s != null && s < 500,
        ));

  Future<UserInfo?> me() async {
    final r = await _dio.get('/me');
    if (r.statusCode == 200) return UserInfo.fromJson(r.data);
    return null;
  }

  Future<UserInfo> login(String email) async {
    final r = await _dio.post('/auth/login', data: {'email': email});
    if (r.statusCode == 200) return UserInfo.fromJson(r.data);
    throw Exception(r.data['detail'] ?? '로그인 실패');
  }

  Future<void> logout() => _dio.post('/auth/logout');

  Future<List<TemplateInfo>> templates() async {
    final r = await _dio.get('/templates');
    return (r.data as List).map((e) => TemplateInfo.fromJson(e)).toList();
  }

  Future<List<ConfigFieldInfo>> configSchema(String key) async {
    final r = await _dio.get('/templates/$key/config-schema');
    return (r.data as List).map((e) => ConfigFieldInfo.fromJson(e)).toList();
  }

  Future<List<AgentInfo>> agents() async {
    final r = await _dio.get('/agents');
    return (r.data as List).map((e) => AgentInfo.fromJson(e)).toList();
  }

  Future<AgentInfo> agent(String id) async {
    final r = await _dio.get('/agents/$id');
    return AgentInfo.fromJson(r.data);
  }

  Future<AgentInfo> createAgent(String templateKey, String name,
      Map<String, dynamic> config, Map<String, dynamic> secrets) async {
    final r = await _dio.post('/agents', data: {
      'template_key': templateKey,
      'name': name,
      'config': config,
      'secrets': secrets,
    });
    return AgentInfo.fromJson(r.data);
  }

  Future<AgentInfo> updateAgent(String id,
      {String? name, Map<String, dynamic>? config, Map<String, dynamic>? secrets}) async {
    final r = await _dio.patch('/agents/$id', data: {
      if (name != null) 'name': name,
      if (config != null) 'config': config,
      if (secrets != null && secrets.isNotEmpty) 'secrets': secrets,
    });
    return AgentInfo.fromJson(r.data);
  }

  Future<void> deleteAgent(String id) => _dio.delete('/agents/$id');

  Future<void> runNow(String id, {bool dryRun = false}) =>
      _dio.post('/agents/$id/run', queryParameters: {'dry_run': dryRun});

  Future<List<ProjectInfo>> projects(String agentId) async {
    final r = await _dio.get('/agents/$agentId/projects');
    return (r.data as List).map((e) => ProjectInfo.fromJson(e)).toList();
  }

  Future<void> setProjectStatus(String agentId, String projectId, String status) =>
      _dio.patch('/agents/$agentId/projects/$projectId/status', data: {'status': status});

  Future<List<RunInfo>> runs(String agentId) async {
    final r = await _dio.get('/agents/$agentId/runs');
    return (r.data as List).map((e) => RunInfo.fromJson(e)).toList();
  }

  Future<Map<String, dynamic>?> schedule(String agentId) async {
    final r = await _dio.get('/agents/$agentId/schedule');
    return r.data == null ? null : Map<String, dynamic>.from(r.data);
  }

  Future<void> toggleSchedule(String agentId, bool enabled) =>
      _dio.patch('/agents/$agentId/schedule', data: {'enabled': enabled});
}
