import 'package:drift/drift.dart';
import '../../../core/database/app_database.dart';

class UserRepository {
  final AppDatabase db;
  const UserRepository(this.db);

  Future<User?> getCurrentUser() async {
    final rows = await (db.select(db.users)
          ..orderBy([(t) => OrderingTerm(expression: t.id, mode: OrderingMode.desc)])
          ..limit(1))
        .get();
    return rows.isEmpty ? null : rows.first;
  }

  Stream<User?> watchCurrentUser() {
    final query = (db.select(db.users)
      ..orderBy([(t) => OrderingTerm(expression: t.id, mode: OrderingMode.desc)])
      ..limit(1));
    return query.watch().map((rows) => rows.isEmpty ? null : rows.first);
  }

  Future<int> register({
    required String fullName,
    String? phone,
    String? email,
    String? avatarPath,
  }) async {
    return db.into(db.users).insert(
          UsersCompanion.insert(
            fullName: fullName,
            phone: Value(phone),
            email: Value(email),
            avatarPath: Value(avatarPath),
          ),
        );
  }

  Future<void> updateProfile(User user) async {
    await db.update(db.users).replace(user);
  }

  Future<void> deleteUser(int id) async {
    await (db.delete(db.users)..where((t) => t.id.equals(id))).go();
  }
}
