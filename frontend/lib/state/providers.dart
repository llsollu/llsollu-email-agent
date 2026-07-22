import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/models.dart';

final apiProvider = Provider<ApiClient>((ref) => ApiClient());

/// 현재 로그인 사용자. null 이면 미로그인.
final currentUserProvider = StateProvider<UserInfo?>((ref) => null);

/// 내 에이전트 목록.
final agentsProvider = FutureProvider<List<AgentInfo>>((ref) async {
  ref.watch(currentUserProvider); // 로그인 변화 시 갱신
  return ref.watch(apiProvider).agents();
});

final templatesProvider = FutureProvider<List<TemplateInfo>>((ref) async {
  return ref.watch(apiProvider).templates();
});
