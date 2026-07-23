/// 로컬 저장소 추상화. 웹에서는 localStorage, 그 외 플랫폼에서는 no-op.
library;

export 'local_store_stub.dart' if (dart.library.html) 'local_store_web.dart';
