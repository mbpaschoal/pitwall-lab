"""Explicit, source-backed adjudications; never alter captured bytes or forecasts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from pitwall.data.archive_collection import instant


def load_review(root, event):
    path = Path(root) / 'operacao2026/adjudicacoes' / '{}-{}-{}.json'.format(
        event['temporada'], event['rodada'], event['circuito_id'])
    if not path.exists():
        return None
    review = json.loads(path.read_text())
    expected = {k:event[k] for k in ('temporada','rodada','circuito_id')}
    if review.get('schema') != 'pitwall-weekend-adjudication-v1' or review.get('identidade') != expected:
        raise ValueError('Foreign adjudication identity')
    if review.get('meeting_key') != event['sessions'][0]['meeting_key']:
        raise ValueError('Foreign adjudication meeting')
    for source in review['fontes'].values():
        if source.get('status') != 200 or not re.fullmatch('[a-f0-9]{64}',source.get('sha256','')):
            raise ValueError('Unverified adjudication source')
    review['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return review


def session_review(review, session):
    item = (review or {}).get('sessoes', {}).get(str(session['session_key']))
    if item and (item['session_name'] != session['session_name']
                 or instant(item['inicio_utc']) != instant(session['date_start'])
                 or review['meeting_key'] != session['meeting_key']):
        raise ValueError('Foreign adjudication session')
    return item


def sources(review, names):
    return [review['fontes'][name] for name in names]


def _documented_stints(output, item, session, review, audit):
    """Admit only reviewed compounds; do not import alternative lap times/ages."""
    if 'laps' not in output or 'stints' not in output:
        return
    for correction in item.get('stints_documentados', []):
        number = correction['driver_number']
        profile = [r for r in output['drivers'] if r['driver_number'] == number]
        if len(profile) != 1 or any(profile[0].get(k) != correction[k] for k in ('full_name', 'team_name')):
            raise ValueError('Documented tyre identity mismatch')
        start, end = correction['lap_start'], correction['lap_end']
        window = correction['intervalo_sem_boxes']
        if (type(start) is not int or type(end) is not int or not 0 < start <= end
                or window['voltas'] != end-start+1 or correction['compound'] not in ('SOFT','MEDIUM','HARD','INTERMEDIATE','WET')
                or not instant(session['date_start']) <= instant(window['inicio_utc']) < instant(window['fim_utc']) <= instant(session['date_end'])):
            raise ValueError('Invalid documented tyre interval')
        rows = {r['lap_number']: r for r in output['laps'] if r['driver_number'] == number}
        checked = correction['voltas_verificadas']
        if [r['lap_number'] for r in checked] != list(range(start+1, end+1)):
            raise ValueError('Incomplete direct compound evidence')
        for expected in checked:
            row = rows.get(expected['lap_number'], {})
            if (row.get('lap_duration') != expected['lap_duration'] or not row.get('date_start')
                    or not instant(window['inicio_utc']) <= instant(row['date_start']) < instant(window['fim_utc'])):
                raise ValueError('Documented tyre evidence differs from native laps')
        initial = correction['registro_inicial_sem_tempo']
        if initial['lap_number'] != start or start not in rows or any(rows[start].get(k) != initial[k] for k in ('date_start','lap_duration')):
            raise ValueError('Initial unmeasured lap changed; review tyre continuity')
        overlaps = [r for r in output['stints'] if r['driver_number'] == number
                    and type(r.get('lap_start')) is int and type(r.get('lap_end')) is int
                    and max(start, r['lap_start']) <= min(end, r['lap_end'])]
        if overlaps:
            if len(overlaps) != 1 or any(overlaps[0].get(k) != correction[k] for k in ('stint_number','lap_start','lap_end','compound')):
                raise ValueError('Native stint contradicts documentary correction')
            stint = overlaps[0]  # Preserve a compatible native age, including zero.
        else:
            stint = dict(session_key=session['session_key'], meeting_key=session['meeting_key'],
                         **{k: correction[k] for k in ('driver_number','stint_number','lap_start','lap_end','compound','tyre_age_at_start')})
            output['stints'].append(stint)
        stint['revisao_composto'] = dict(metodo=correction['metodo'],
            voltas_diretas=[r['lap_number'] for r in checked],
            primeira_volta_por_continuidade=start, fontes=sources(review, correction['fontes']))
        audit['acoes'].append(dict(tipo='composto_documentado', numero=number,
            inicio=start, fim=end, composto=correction['compound'],
            metodo=correction['metodo'], fontes=sources(review, correction['fontes'])))


def reconcile(data, session, review):
    item = session_review(review, session)
    if not item:
        return data, None
    output = deepcopy(data)
    audit = dict(id=review['id'],sha256=review['sha256'],acoes=[])
    if item.get('recorte_pit'):
        before = instant(session['date_start'])
        excluded = [i for i,r in enumerate(output.get('pit',[])) if r.get('date') and instant(r['date']) < before]
        output['pit'] = [r for i,r in enumerate(output.get('pit',[])) if i not in excluded]
        audit['acoes'].append(dict(tipo='pit_contexto_anterior',indices_fonte=excluded,
                                  limite_utc=session['date_start'],fontes=sources(review,[
                                      'fp3_on_track' if session['session_name']=='Practice 3' else 'q_on_track'])))
    for profile in item.get('perfis',[]):
        existing = [d for d in output['drivers'] if d['driver_number']==profile['driver_number']]
        if existing:
            if len(existing)!=1 or any(existing[0].get(k)!=profile[k] for k in ('first_name','last_name','team_name')):
                raise ValueError('Profile contradicts reviewed identity')
            continue
        result = [r for r in output['session_result'] if r['driver_number']==profile['driver_number']]
        if len(result)!=1 or any(result[0].get(k)!=v for k,v in profile['resultado_esperado'].items()):
            raise ValueError('Profile evidence does not match native result')
        output['drivers'].append(dict({k:v for k,v in profile.items() if k not in ('fontes','resultado_esperado')},
                                      session_key=session['session_key'],meeting_key=session['meeting_key']))
        audit['acoes'].append(dict(tipo='perfil_documentado',numero=profile['driver_number'],fontes=sources(review,profile['fontes'])))
    for decision in item.get('desclassificacoes',[]):
        drivers = [d for d in output['drivers'] if d['driver_number']==decision['driver_number']]
        if len(drivers)!=1 or any(drivers[0].get(k)!=decision[k] for k in ('full_name','team_name')):
            raise ValueError('Disqualification identity mismatch')
        results = [r for r in output['session_result'] if r['driver_number']==decision['driver_number']]
        if len(results)!=1:
            raise ValueError('Disqualification result missing/duplicated')
        result=results[0]
        audit['acoes'].append(dict(tipo='desclassificacao_oficial',numero=decision['driver_number'],
            anterior={k:result.get(k) for k in ('position','duration','dsq','number_of_laps')},fontes=sources(review,decision['fontes'])))
        result.update(position=None,dsq=True,duration=[None,None,None],gap_to_leader=None,
                      fonte_validacao=review['fontes'][decision['fontes'][0]]['url'])
    final = item.get('classificacao_final')
    if final:
        from operacao2026.final_results import final_source, reconcile_native
        source = final_source(review, final)
        previous = reconcile_native(output, final, source)
        audit['acoes'].append(dict(tipo='classificacao_final_oficial', anterior=previous,
                                  fontes=sources(review, [final['fonte']])))
    _documented_stints(output, item, session, review, audit)
    return output, audit


def mark_tyre_gaps(entry, session, review):
    """Receiving stint rows does not establish coverage of every observed lap."""
    item = session_review(review,session) or {}
    for gap in item.get('pneus_ausentes',[]):
        for strategy in entry.get('dados_descritivos',{}).get('estrategias',[]):
            if strategy['numero'] != gap['driver_number']:
                continue
            covered = {lap for stint in strategy['sequencia_stints']
                       if type(stint.get('inicio')) is int and type(stint.get('fim')) is int
                       for lap in range(stint['inicio'],stint['fim']+1)}
            missing = sorted(set(range(gap['lap_start'],gap['lap_end']+1))-covered)
            if not missing:
                continue
            strategy['comparavel']=False
            strategy['qualidade'].append(dict(flags=['composto_inicial_ausente'],voltas=missing))
            entry['estado']='parcial'
            entry['motivo_parcial']='Composto do stint inicial de Lawson ainda indisponível; tempos e paradas recuperados.'
            entry.setdefault('lacunas_documentadas',[]).append(dict(
                grupo='pneus',numero=gap['driver_number'],voltas=missing,fontes=sources(review,[gap['fonte']])))
