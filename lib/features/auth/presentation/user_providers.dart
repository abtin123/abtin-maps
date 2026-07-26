import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/database/app_database.dart';
import '../../../core/database/database_provider.dart';
import '../data/user_repository.dart';

final userRepositoryProvider = Provider<UserRepository>((ref) {
  return UserRepository(ref.watch(appDatabaseProvider));
});

final currentUserProvider = StreamProvider<User?>((ref) {
  return ref.watch(userRepositoryProvider).watchCurrentUser();
});
