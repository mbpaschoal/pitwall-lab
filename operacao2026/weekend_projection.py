"""Thin descriptive projection of native session data, without canonical joins."""
from collections import defaultdict

def project(data, session):
    drivers = {d['driver_number']: d for d in data.get('drivers', [])}
    laps = defaultdict(list)
    seen = {}
    for row in data.get('laps', []):
        (number, lap) = (row.get('driver_number'), row.get('lap_number'))
        if number not in drivers or type(lap) is not int or lap < 1:
            raise ValueError('Lap identity unavailable')
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
            raise ValueError('Tyre identity unavailable')
        stints[number].append(dict(inicio=row.get('lap_start'), fim=row.get('lap_end'), composto=row.get('compound'), idade=row.get('tyre_age_at_start')))
    strategies = []
    for (number, rows) in stints.items():
        known = all((type(s['inicio']) is int and type(s['fim']) is int and (0 < s['inicio'] <= s['fim']) and (s['composto'] in ('SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET')) for s in rows))
        strategies.append(dict(numero=number, piloto=drivers[number].get('full_name'), equipe=drivers[number].get('team_name'), modalidade=session['session_name'], session_key=session['session_key'], sequencia_stints=rows, comparavel=known, qualidade=[] if known else [{'flags': ['limites_ou_composto_ausentes']}]))
    pits = []
    for row in data.get('pit', []):
        number = row.get('driver_number')
        if number not in drivers:
            raise ValueError('Pit identity unavailable')
        pits.append(dict(numero=number, piloto=drivers[number].get('full_name'), equipe=drivers[number].get('team_name'), volta=row.get('lap_number'), duracao_s=row.get('pit_duration'), fonte='https://openf1.org/docs/#pit'))
    return dict(voltas_por_piloto=history, estrategias=strategies, paradas=pits)
