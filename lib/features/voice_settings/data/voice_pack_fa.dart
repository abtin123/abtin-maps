library;

enum VoiceGender { female, male }

class VoicePackFa {
  VoicePackFa._();

  static String assetFolder = 'voice/fa';

  static void setGender(VoiceGender gender) {
    assetFolder = gender == VoiceGender.male ? 'voice/fa_male' : 'voice/fa';
  }

  static List<String> distance(double meters) {
    final dist = meters;
    if (dist < 17) {
      return [..._oggDist(dist.round()), 'meters.ogg'];
    } else if (dist < 100) {
      return [..._oggDist((dist / 10.0).round() * 10), 'meters.ogg'];
    } else if (dist < 1000) {
      return [..._oggDist(((2 * dist / 100.0).round() * 50)), 'meters.ogg'];
    } else if (dist < 1500) {
      return ['around_1_kilometer.ogg'];
    } else if (dist < 10000) {
      return ['around.ogg', ..._oggDist((dist / 1000.0).round()), 'kilometers.ogg'];
    } else {
      return [..._oggDist((dist / 1000.0).round()), 'kilometers.ogg'];
    }
  }

  static List<String> _oggDist(int distance) {
    if (distance <= 0) return const [];
    if (distance < 20) {
      return ['$distance.ogg'];
    } else if (distance < 1000 && (distance % 50) == 0) {
      return ['$distance.ogg'];
    } else if (distance < 30) {
      return ['20.ogg', ..._oggDist(distance - 20)];
    } else if (distance < 40) {
      return ['30.ogg', ..._oggDist(distance - 30)];
    } else if (distance < 50) {
      return ['40.ogg', ..._oggDist(distance - 40)];
    } else if (distance < 60) {
      return ['50.ogg', ..._oggDist(distance - 50)];
    } else if (distance < 70) {
      return ['60.ogg', ..._oggDist(distance - 60)];
    } else if (distance < 80) {
      return ['70.ogg', ..._oggDist(distance - 70)];
    } else if (distance < 90) {
      return ['80.ogg', ..._oggDist(distance - 80)];
    } else if (distance < 100) {
      return ['90.ogg', ..._oggDist(distance - 90)];
    } else if (distance < 200) {
      return ['100.ogg', ..._oggDist(distance - 100)];
    } else if (distance < 300) {
      return ['200.ogg', ..._oggDist(distance - 200)];
    } else if (distance < 400) {
      return ['300.ogg', ..._oggDist(distance - 300)];
    } else if (distance < 500) {
      return ['400.ogg', ..._oggDist(distance - 400)];
    } else if (distance < 600) {
      return ['500.ogg', ..._oggDist(distance - 500)];
    } else if (distance < 700) {
      return ['600.ogg', ..._oggDist(distance - 600)];
    } else if (distance < 800) {
      return ['700.ogg', ..._oggDist(distance - 700)];
    } else if (distance < 900) {
      return ['800.ogg', ..._oggDist(distance - 800)];
    } else if (distance < 1000) {
      return ['900.ogg', ..._oggDist(distance - 900)];
    } else {
      return [..._oggDist(distance ~/ 1000), '1000.ogg', ..._oggDist(distance % 1000)];
    }
  }

  static List<String> time(double seconds) {
    final minutes = (seconds / 60.0).round();
    if (seconds < 30) return ['less_a_minute.ogg'];
    if (seconds < 300) return [..._oggDist(minutes), 'minutes.ogg'];
    final oggMinutes = ((seconds / 300.0) * 5).round();
    if (oggMinutes % 60 > 0) {
      return [..._hours(oggMinutes), ..._oggDist(oggMinutes % 60), 'minutes.ogg'];
    }
    return _hours(oggMinutes);
  }

  static List<String> _hours(int minutes) {
    if (minutes < 60) return const [];
    if (minutes < 120) return ['1_hour.ogg'];
    final hrs = minutes ~/ 60;
    return [..._oggDist(hrs), 'hours.ogg'];
  }

  static String? turnFile(String? modifier) {
    if (modifier == null) return null;
    final m = modifier.toLowerCase();
    if (m.contains('sharp right')) return 'right_sh.ogg';
    if (m.contains('sharp left')) return 'left_sh.ogg';
    if (m.contains('slight right')) return 'right_sl.ogg';
    if (m.contains('slight left')) return 'left_sl.ogg';
    if (m.contains('uturn')) return null;
    if (m.contains('right')) return 'right.ogg';
    if (m.contains('left')) return 'left.ogg';
    if (m.contains('straight')) return 'go_ahead.ogg';
    return null;
  }

  static String? nth(int exit) {
    if (exit < 1 || exit > 17) return null;
    const ordinals = [
      '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th',
      '11th', '12th', '13th', '14th', '15th', '16th', '17th',
    ];
    return '${ordinals[exit - 1]}.ogg';
  }

  static List<String> forManeuver({
    required String type,
    String? modifier,
    int? exit,
    double? distanceMeters,
  }) {
    final prefix = (distanceMeters != null && distanceMeters > 0)
        ? ['in.ogg', ...distance(distanceMeters)]
        : <String>[];

    if (type == 'arrive') {
      return ['reached_destination.ogg'];
    }
    if (type == 'depart') {
      return const ['route_calculate.ogg'];
    }
    if (type == 'roundabout' || type == 'rotary') {
      final nthFile = (exit != null) ? nth(exit) : null;
      return [
        ...prefix,
        'roundabout.ogg',
        'and.ogg',
        'take.ogg',
        if (nthFile != null) nthFile,
        'exit.ogg',
      ];
    }
    if (modifier != null && modifier.toLowerCase().contains('uturn')) {
      return [...prefix, 'make_uturn.ogg'];
    }
    if (type == 'new name' || type == 'continue') {
      if (distanceMeters != null && distanceMeters > 0) {
        return ['follow.ogg', ...distance(distanceMeters)];
      }
      return ['go_ahead.ogg'];
    }

    final turn = turnFile(modifier);
    if (turn != null) {
      return [...prefix, turn];
    }
    return [...prefix, 'go_ahead.ogg'];
  }

  static List<String> routeCalculated({required double distanceMeters, required double durationSeconds}) {
    return [
      'route_calculate.ogg',
      'distance.ogg',
      ...distance(distanceMeters),
      'time.ogg',
      ...time(durationSeconds),
    ];
  }

  static const List<String> arrived = ['reached_destination.ogg'];
  static const List<String> gpsLost = ['location_lost.ogg'];
  static const List<String> gpsRecovered = ['location_recovered.ogg'];

  static List<String> offRoute(double distanceMeters) => [
        'off_route.ogg',
        ...distance(distanceMeters),
      ];
}
