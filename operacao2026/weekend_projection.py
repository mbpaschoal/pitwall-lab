"""Thin descriptive projection of native session data, without canonical joins."""
from collections import defaultdict

class DriverIdentityUnavailable(ValueError):
    """A session's native number has no profile; withhold its projections."""

    def __init__(self, numbers):
        self.numbers = sorted(numbers) if isinstance(numbers, (list, set, tuple)) else [numbers]
        super().__init__('Driver profile unavailable: {}'.format(self.numbers))
        self.number = self.numbers[0]


def verify_driver_profiles(data, endpoints=('session_result', 'laps', 'stints', 'pit')):
    """Check all conflicts before treating an absent profile as retryable."""
    numbers = [row.get('driver_number') for row in data.get('drivers', [])]
    if any(type(n) is not int or n <= 0 for n in numbers) or len(numbers) != len(set(numbers)):
        raise ValueError('Driver number invalid/duplicated')
    known, missing, results, laps = set(numbers), set(), set(), {}
    for endpoint in ('session_result', 'laps', 'stints', 'pit'):
        for row in data.get(endpoint, []):
            number = row.get('driver_number')
            if type(number) is not int or number <= 0:
                raise ValueError('Native driver number invalid')
            if endpoint == 'session_result':
                if number in results:
                    raise ValueError('Result identity invalid/duplicated')
                results.add(number)
            if endpoint == 'laps':
                lap = row.get('lap_number')
                if type(lap) is not int or lap < 1:
                    raise ValueError('Lap identity unavailable')
                key = number, lap
                if key in laps and laps[key] != row:
                    raise ValueError('Conflicting duplicate lap')
                laps[key] = row
            if number not in known and endpoint in endpoints:
                missing.add(number)
    if missing:
        raise DriverIdentityUnavailable(missing)


def project(data, session):
    verify_driver_profiles(data)
    drivers = {d['driver_number']: d for d in data.get('drivers', [])}
    laps = defaultdict(list)
    seen = {}
    for row in data.get('laps', []):
        (number, lap) = (row.get('driver_number'), row.get('lap_number'))
        if type(lap) is not int or lap < 1:
            raise ValueError('Lap identity unavailable')
        if number not in drivers:
            raise DriverIdentityUnavailable(number)
        key = (number, lap)
        if key in seen and seen[key] != row:
            raise ValueError('Conflicting duplicate lap')
        if key in seen:
            continue
        seen[key] = row
        laps[number].append([lap, row.get('lap_duration')])
    history = [dict(piloto=drivers[n].get('full_name'), piloto_id='openf1:{}'.format(n), voltas=sorted(rows)) for (n, rows) in laps.items()]
    stints = defaultdict(list)
    for row in data.get('stints', []):
        number = row.get('driver_number')
        if number not in drivers:
            raise DriverIdentityUnavailable(number)
        stints[number].append(dict(inicio=row.get('lap_start'), fim=row.get('lap_end'), composto=row.get('compound'), idade=row.get('tyre_age_at_start')))
    strategies = []
    for (number, rows) in stints.items():
        known = all((type(s['inicio']) is int and type(s['fim']) is int and (0 < s['inicio'] <= s['fim']) and (s['composto'] in ('SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET')) for s in rows))
        strategies.append(dict(numero=number, piloto=drivers[number].get('full_name'), equipe=drivers[number].get('team_name'), modalidade=session['session_name'], session_key=session['session_key'], sequencia_stints=rows, comparavel=known, qualidade=[] if known else [{'flags': ['limites_ou_composto_ausentes']}]))
    pits = []
    for row in data.get('pit', []):
        number = row.get('driver_number')
        if number not in drivers:
            raise DriverIdentityUnavailable(number)
        pits.append(dict(numero=number, piloto=drivers[number].get('full_name'), equipe=drivers[number].get('team_name'), volta=row.get('lap_number'), duracao_s=row.get('pit_duration'), fonte='https://openf1.org/docs/#pit'))
    return dict(voltas_por_piloto=history, estrategias=strategies, paradas=pits)
