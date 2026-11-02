"""Apply explicitly reviewed final classifications without rewriting captures."""
import math

from pitwall.data.archive_collection import instant


def validated_rows(final):
    rows = final['linhas']
    if not rows or any(type(r['numero']) is not int or r['numero'] <= 0 for r in rows):
        raise ValueError('Invalid final result numbers')
    for key in ('numero', 'piloto_id', 'ordem'):
        if len({r[key] for r in rows}) != len(rows):
            raise ValueError('Duplicated final result identity/order')
    if {r['ordem'] for r in rows} != set(range(1, len(rows) + 1)):
        raise ValueError('Incomplete final result order')
    classified = [r for r in rows if r['posicao'] is not None]
    if {r['posicao'] for r in classified} != set(range(1, len(classified) + 1)):
        raise ValueError('Invalid final classified positions')
    for row in rows:
        if (not isinstance(row['piloto_id'], str) or not row['piloto_id']
                or type(row['ordem']) is not int
                or type(row['voltas']) is not int or row['voltas'] < 0
                or type(row['pontos']) not in (int, float)
                or not math.isfinite(row['pontos']) or row['pontos'] < 0
                or (row['posicao'] is None) != (row['situacao'] == 'NC')):
            raise ValueError('Invalid final result row')
        if row['posicao'] is not None and (
                type(row['posicao']) is not int or row['posicao'] != row['ordem']
                or any(type(row[k]) not in (int, float) or not math.isfinite(row[k])
                       or row[k] < 0 for k in ('duracao', 'gap'))):
            raise ValueError('Invalid final result timing')
        if row['posicao'] is None and (row['duracao'] is not None or row['gap'] is not None
                                      or row['pontos'] != 0):
            raise ValueError('Unclassified result must retain unknown finish time')
    return rows


def final_source(review, final):
    source = review['fontes'][final['fonte']]
    if (source.get('endpoint') != 'final_race'
            or not source['url'].startswith('https://www.fia.com/')
            or not source['url'].endswith('_final_race_classification.pdf')
            or instant(source['obtido_em_utc']) <= instant(final['encerramento_observado_utc'])):
        raise ValueError('Final result source is not verified posterior FIA evidence')
    return source


def reconcile_native(data, final, source):
    """Require the same complete native population and literal driver profiles."""
    rows = validated_rows(final)
    numbers = {r['numero'] for r in rows}
    results = data['session_result']
    profiles = data['drivers']
    if (len(results) != len(rows) or {r['driver_number'] for r in results} != numbers
            or len(profiles) != len(rows) or {p['driver_number'] for p in profiles} != numbers):
        raise ValueError('Final result population mismatch')
    drivers = {p['driver_number']: p for p in profiles}
    for row in rows:
        profile = drivers[row['numero']]
        if (profile.get('full_name') != row['full_name']
                or profile.get('team_name') not in (None, row['team_name'])):
            raise ValueError('Final result profile mismatch')
    by_number = {r['numero']: r for r in rows}
    previous = []
    for result in results:
        row = by_number[result['driver_number']]
        previous.append({k: result.get(k) for k in (
            'driver_number', 'position', 'duration', 'gap_to_leader', 'points', 'number_of_laps')})
        result.update(position=row['posicao'], duration=row['duracao'],
                      gap_to_leader=row['gap'], points=row['pontos'],
                      number_of_laps=row['voltas'],
                      dnf=row['situacao'] == 'NC', dsq=False, fonte_validacao=source['url'])
    results.sort(key=lambda result: by_number[result['driver_number']]['ordem'])
    return previous


