import 'package:go_router/go_router.dart';
import '../../features/map/presentation/home_screen.dart';
import '../../features/search/presentation/search_screen.dart';
import '../../features/routes/presentation/routes_screen.dart';
import '../../features/settings/presentation/settings_screen.dart';
import '../../features/voice_settings/presentation/voice_settings_screen.dart';
import '../../features/saved_places/presentation/saved_places_screen.dart';
import '../../features/offline_maps/presentation/map_settings_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
    GoRoute(path: '/search', builder: (context, state) => const SearchScreen()),
    GoRoute(path: '/routes', builder: (context, state) => const RoutesScreen()),
    GoRoute(path: '/settings', builder: (context, state) => const SettingsScreen()),
    GoRoute(
      path: '/voice-settings',
      builder: (context, state) => const VoiceSettingsScreen(),
    ),
    GoRoute(
      path: '/saved-places',
      builder: (context, state) => const SavedPlacesScreen(),
    ),
    GoRoute(
      path: '/map-settings',
      builder: (context, state) => const MapSettingsScreen(),
    ),
  ],
);
