"""Exportação offline do acervo validado para apresentação pública compacta."""
import argparse
from collections import defaultdict
import csv
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path

from acervo_dashboard_dados import ASSET, SCHEMA, VERSAO, conteudo_sha256, validar

RAIZ = Path(__file__).resolve().parent
ACERVO = 'data/acervo_historico/coleta-20261027T230248Z'


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _hash(path):
    digest = sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _number(value, integer=False):
    if value in ('', None):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Valor não finito na fonte.')
    if integer:
        if not result.is_integer():
            raise ValueError('Contagem não inteira na fonte.')
        return int(result)
    return result


def _bool(value):
    if value in ('', None):
        return None
    if value not in ('True', 'False'):
        raise ValueError('Indicador inválido na fonte.')
    return value == 'True'


def _position(value):
    try:
        result = _number(value, True)
        return result if result is not None and result > 0 else None
    except ValueError:
        return None


def _time(value):
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise ValueError('Duração inválida na fonte.')
    milliseconds = round(value * 1000)
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return ('{}:{:02d}:{:02d}.{:03d}'.format(hours, minutes, seconds, millis) if hours
            else '{}:{:02d}.{:03d}'.format(minutes, seconds, millis))


def _gap(value):
    if value is None:
        return None
    if isinstance(value, list):
        return ' / '.join('Q{} {}'.format(i + 1, _gap(v) or '—') for i, v in enumerate(value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return '{:.3f} s'.format(value)
    return str(value)


def _key(row):
    return '{}:{}'.format(int(row['temporada']), int(row['rodada']))


def _display(pid, name):
    return 'Andrea Kimi Antonelli' if pid == 'antonelli' and name == 'Kimi Antonelli' else name


def preparar(raiz=RAIZ, acervo=None, destino=None):
    root = Path(raiz)
    source = Path(acervo) if acervo is not None else root / ACERVO
    target = Path(destino) if destino is not None else root / ASSET
    local = _json(source / 'local/inventario_local.json')
    normalized = _json(source / 'normalizado/manifesto.json')
    manifests = {'local': local['arquivos_sha256'], 'normalizado': normalized['arquivos']}
    for layer, files in manifests.items():
        for name, digest in files.items():
            path = source / layer / name
            if path.is_symlink() or _hash(path) != digest:
                raise ValueError('Fonte do acervo divergente: {}/{}'.format(layer, name))

    def rows(layer, name):
        if name not in manifests[layer]:
            raise ValueError('Tabela ausente do manifesto: ' + name)
        with (source / layer / name).open(encoding='utf-8', newline='') as handle:
            yield from csv.DictReader(handle)

    events = _json(source / 'local/eventos.json')
    gps = {}
    for event in events:
        key = _key(event)
        if key in gps:
            raise ValueError('GP duplicado no acervo.')
        gps[key] = {
            'identidade': {k: event[k] for k in ('temporada', 'rodada', 'circuito_id')},
            'corrida': event['corrida'], 'data_corrida': event['data_corrida'],
            'sessoes': [], 'clima': {'horas': [], 'resumo': {}, 'pista_sessoes': [],
                'modelo': 'ecmwf_ifs', 'origem': 'modelo atmosférico histórico em grade',
                'atribuicao': 'Weather data by Open-Meteo.com (CC BY 4.0)', 'url': 'https://open-meteo.com/'},
            'estrategias': [], 'paradas': [], 'equipes': [], 'cobertura': [],
            'campeonato_pilotos': {}, 'campeonato_equipes': {},
            'historico': {'resultados': [], 'voltas_por_piloto': [], 'resumo': {}},
            'aviso': 'Acervo descritivo. Estes dados não alteram as probabilidades publicadas.',
        }

    def gp_for(row):
        key = _key(row)
        gp = gps.get(key)
        if gp is None or gp['identidade']['circuito_id'] != row['circuito_id']:
            raise ValueError('Tabela ligada ao GP/circuito incorreto.')
        return gp

    people = {}; names_by_year = {}; team_labels = {}; native = {}
    for row in rows('local', 'resultados.csv'):
        gp = gp_for(row); key = _key(row); pid = row['piloto_id']
        name = _display(pid, row['piloto'])
        people[(key, pid)] = name; names_by_year[(int(row['temporada']), pid)] = name
        gp['historico']['resultados'].append({
            'piloto_id': pid, 'piloto': name, 'equipe_id': row['equipe_id'],
            'equipe': row['equipe_id'].replace('_', ' ').title(),
            'posicao': _number(row['posicao_final'], True), 'pontos': _number(row['pontos']),
            'voltas': _number(row['voltas'], True), 'status': row['status'], 'tempo': row['tempo_original'] or None,
        })
    for row in rows('normalizado', 'pilotos_sessoes.csv'):
        gp_for(row); key = _key(row)
        native[(int(row['session_key']), int(row['driver_number']))] = row
        if row['equipe_id'] and row['team_name_openf1']:
            team_labels[(key, row['equipe_id'])] = row['team_name_openf1']

    def person(row):
        key = _key(row); skey = int(row['session_key']); number = int(row['driver_number'])
        registry = native.get((skey, number), {})
        return {'piloto_id': row.get('piloto_id') or None, 'numero': number,
                'piloto': people.get((key, row.get('piloto_id'))) or registry.get('full_name') or '#{}'.format(number),
                'equipe': registry.get('team_name_openf1') or team_labels.get((key, row.get('equipe_id'))) or None}

    sessions = {}
    for row in rows('normalizado', 'sessoes.csv'):
        gp = gp_for(row); skey = int(row['session_key'])
        if skey in sessions:
            raise ValueError('Sessão duplicada no acervo.')
        session = {'session_key': skey, 'nome': row['session_name'], 'tipo': row['session_type'],
                   'inicio_utc': row['date_start'], 'fim_utc': row['date_end'], 'n_voltas': 0, 'tempos': [],
                   'criterio_data': row['metodo_mapeamento'], 'data_calendario': row['data_corrida_calendario']}
        sessions[skey] = (gp, session); gp['sessoes'].append(session)
    for row in rows('normalizado', 'tempos_sessoes.csv'):
        gp = gp_for(row); skey = int(row['session_key'])
        if skey not in sessions or sessions[skey][0] is not gp:
            raise ValueError('Tempos ligados a sessão/GP incorreto.')
        duration = json.loads(row['duration_original_json']); gap = json.loads(row['gap_to_leader_original_json'])
        phases = duration if isinstance(duration, list) else []
        valid = [x for x in phases if x is not None]
        displayed = valid[-1] if valid else None if isinstance(duration,list) else duration
        item = person(row)
        item.update(posicao=_position(row['position']), posicao_original=row['position'] or None,
                    duracao=_time(displayed), gap=_gap(gap),
                    duracao_original=duration, gap_original=gap, voltas=_number(row['number_of_laps'], True),
                    q1=_time(phases[0]) if len(phases) > 0 else None,
                    q2=_time(phases[1]) if len(phases) > 1 else None,
                    q3=_time(phases[2]) if len(phases) > 2 else None)
        sessions[skey][1]['tempos'].append(item)
    lap_groups = defaultdict(list)
    for row in rows('normalizado', 'laps_sessoes.csv'):
        gp = gp_for(row); skey = int(row['session_key'])
        if skey not in sessions or sessions[skey][0] is not gp:
            raise ValueError('Volta ligada a sessão/GP incorreto.')
        sessions[skey][1]['n_voltas'] += 1
        if row['session_name'] == 'Race':
            item = person(row); identity = (_key(row), item['piloto_id'] or 'openf1:{}'.format(item['numero']))
            lap_groups[identity].append((_number(row['lap_number'], True), _number(row['lap_duration']), item))
    for (key, _), laps in lap_groups.items():
        ordered = sorted(laps, key=lambda x: x[0]); item = ordered[0][2]
        durations = [x[1] for x in ordered if x[1] is not None]
        gps[key]['historico']['voltas_por_piloto'].append(dict(item,
            voltas=[[n, duration, None] for n, duration, _ in ordered], n_voltas=len(ordered),
            melhor_volta_s=min(durations) if durations else None,
            volta_media_s=sum(durations) / len(durations) if durations else None))

    for row in rows('normalizado', 'clima_open_meteo.csv'):
        gp = gp_for(row)
        gp['clima']['horas'].append({'data_utc': row['date_utc'], 'temperatura_c': _number(row['temperature_2m']),
            'umidade': _number(row['relative_humidity_2m']), 'precipitacao_mm': _number(row['precipitation']),
            'vento_ms': _number(row['wind_speed_10m']), 'pressao_hpa': _number(row['surface_pressure'])})
        gp['clima']['modelo'] = row['model']; gp['clima']['origem_codigo'] = row['origin']
        if row['origin'] == 'archived_forecast':
            gp['clima']['origem'] = 'previsão arquivada em grade; não é medição da pista'
    track = defaultdict(list)
    for row in rows('normalizado', 'clima_pista.csv'):
        gp_for(row); track[(_key(row), int(row['session_key']))].append(row)
    for (key, skey), observations in track.items():
        def vals(field):
            return [v for v in (_number(row[field]) for row in observations) if v is not None]
        air, asphalt, humidity, wind, rainfall = (vals(f) for f in ('air_temperature','track_temperature','humidity','wind_speed','rainfall'))
        gps[key]['clima']['pista_sessoes'].append({'session_key': skey, 'nome': sessions[skey][1]['nome'],
            'n_medicoes': len(observations), 'temperatura_ar_min_c': min(air) if air else None,
            'temperatura_ar_max_c': max(air) if air else None, 'temperatura_pista_min_c': min(asphalt) if asphalt else None,
            'temperatura_pista_max_c': max(asphalt) if asphalt else None,
            'chuva_observada': any(rainfall) if rainfall else None,
            'umidade_media': sum(humidity)/len(humidity) if humidity else None, 'vento_max_ms': max(wind) if wind else None})
    for row in rows('normalizado', 'estrategias_pneus.csv'):
        gp = gp_for(row); item = person(row)
        sequence = json.loads(row['sequencia_stints_json'])
        item.update(session_key=int(row['session_key']), modalidade=row['session_name'],
                    sequencia_stints=[{'composto': s['compound'], 'inicio': s['lap_start'], 'fim': s['lap_end'],
                                       'idade': s['tyre_age_at_start']} for s in sequence],
                    qualidade=json.loads(row['qualidade_limites_json']), comparavel=_bool(row['limites_voltas_comparaveis']))
        gp['estrategias'].append(item)
    for row in rows('local', 'pit_stops.csv'):
        gp = gp_for(row); key = _key(row)
        gp['paradas'].append({'piloto_id': row['piloto_id'], 'piloto': people.get((key,row['piloto_id']),row['piloto_id']),
            'equipe': team_labels.get((key,row['equipe_id']),row['equipe_id']), 'volta': _number(row['volta'],True),
            'parada': _number(row['parada'],True), 'duracao_s': _number(row['duracao_segundos']),
            'fonte': 'Jolpica-F1 / archive local' if 'archive' in row['fonte_id'] else 'Jolpica-F1',
            'medida': 'duração publicada da passagem/parada; não equivale automaticamente a tempo de troca'})
    for row in rows('normalizado', 'comparativo_equipes.csv'):
        gp = gp_for(row); key = _key(row)
        ids = json.loads(row['pilotos_id_json'])
        gp['equipes'].append({'modalidade': row['tipo_sessao'], 'equipe_id': row['equipe_id'],
            'equipe': team_labels.get((key,row['equipe_id']),row['equipe_id'].replace('_',' ').title()),
            'n_resultados': _number(row['n_resultados'], True), 'pontos': _number(row['pontos_soma_observada']),
            'pontos_completos': _bool(row['pontos_completos']), 'posicao_media': _number(row['posicao_media_observada']),
            'melhor_posicao': _number(row['melhor_posicao_observada'], True),
            'pilotos': [people.get((key,pid),pid) for pid in ids]})
    standings = defaultdict(list); standings_meta = defaultdict(list)
    for kind in ('pilotos','equipes'):
        for row in rows('local', 'campeonato_{}.csv'.format(kind)):
            gp_for(row); key = _key(row); item = {'posicao': _number(row['posicao'],True),
                'pontos': _number(row['pontos']), 'vitorias': _number(row['vitorias'],True)}
            if kind == 'pilotos':
                pid = row['piloto_id']; item.update(piloto_id=pid,
                    piloto=names_by_year.get((int(row['temporada']),pid),pid), equipe_id=None, equipe=None)
            else:
                item.update(equipe_id=row['equipe_id'], equipe=team_labels.get((key,row['equipe_id']),row['equipe_id'].replace('_',' ').title()))
            standings[(key,kind)].append(item)
            standings_meta[(key,kind)].append({'fonte': 'Archive local; publicador da fotografia não confirmado'
                if 'archive' in row['fonte_id'] else 'Jolpica-F1; snapshot local preservado',
                'obtido_em_utc': row['obtido_em_utc']})
    for row in rows('normalizado', 'cobertura.csv'):
        gp = gp_for(row)
        gp['cobertura'].append({k: row[k] for k in ('tipo','provider','estado','motivo')})
    for key,gp in gps.items():
        gp['sessoes'].sort(key=lambda x:x['inicio_utc'])
        for session in gp['sessoes']:
            session['tempos'].sort(key=lambda x:(x['posicao'] is None,x['posicao'] or 9999,x['numero']))
        hours = gp['clima']['horas']; hours.sort(key=lambda x:x['data_utc'])
        def climate_values(field):
            return [h[field] for h in hours if h[field] is not None]
        temperatures, precipitation, wind = (climate_values(k) for k in ('temperatura_c','precipitacao_mm','vento_ms'))
        gp['clima']['resumo'] = {'temperatura_min_c': min(temperatures) if temperatures else None,
            'temperatura_max_c': max(temperatures) if temperatures else None,
            'temperatura_media_c': sum(temperatures)/len(temperatures) if temperatures else None,
            'precipitacao_total_mm': sum(precipitation) if precipitation else None,
            'vento_max_ms': max(wind) if wind else None, 'n_horas':len(hours)}
        for kind in ('pilotos','equipes'):
            records=sorted(standings[(key,kind)],key=lambda x:x['posicao'] or 9999)
            meta = standings_meta[(key,kind)]
            sources = sorted({m['fonte'] for m in meta})
            stamps = sorted({m['obtido_em_utc'] for m in meta})
            gp['campeonato_'+kind]={'disponivel':bool(records),'rodada_referencia':gp['identidade']['rodada'],
                'classificacao':records,'fonte':'; '.join(sources),
                'obtido_em_utc':stamps[-1] if stamps and 'desconhecida' not in stamps else 'desconhecida',
                'escopo':'Fotografia descritiva local; não certifica disponibilidade histórica no corte.',
                'motivo':None if records else 'Classificação não disponível nesta fotografia.'}
        for result in gp['historico']['resultados']:
            result['equipe']=team_labels.get((key,result['equipe_id']),result['equipe'])
        gp['historico']['resultados'].sort(key=lambda x:x['posicao'] or 9999)
        gp['historico']['resumo']={'n_resultados':len(gp['historico']['resultados']),
            'n_voltas':sum(s['n_voltas'] for s in gp['sessoes'] if s['nome']=='Race'),
            'n_pilotos_com_voltas':len(gp['historico']['voltas_por_piloto'])}
    asset={'schema':SCHEMA,'versao':VERSAO,'acervo_origem':source.name,
           'uso':'contexto descritivo retrospectivo; sem alteração das previsões registradas',
           'cobertura':{'gps':len(gps),'sessoes':len(sessions),'voltas_sessoes':normalized['registros']['laps_sessoes']},
           'fontes':[{'nome':'OpenF1','url':'https://openf1.org/','licenca':'CC BY-NC-SA 4.0'},
                     {'nome':'Open-Meteo','url':'https://open-meteo.com/','licenca':'CC BY 4.0'},
                     {'nome':'Jolpica-F1','url':'https://github.com/jolpica/jolpica-f1','licenca':'CC BY-NC-SA 4.0'},
                     {'nome':'Archive local','url':None,'licenca':None,'nota':'Publicador da fotografia não confirmado; UTC de aquisição desconhecida.'}],
           'fontes_normalizadas_sha256':normalized['arquivos'],
           'gps':gps,'conteudo_sha256':conteudo_sha256(gps)}
    validar(asset)
    raw=(json.dumps(asset,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>10*1024*1024:
        raise ValueError('Asset de apresentação excedeu 10MiB.')
    if target.exists():
        if target.read_bytes()!=raw:
            raise FileExistsError('Asset divergente preservado; use destino novo.')
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as handle:handle.write(raw)
    return {'arquivo':str(target),'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'gps':len(gps),'sessoes':len(sessions)}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acervo',type=Path)
    parser.add_argument('--destino',type=Path)
    args=parser.parse_args()
    print(json.dumps(preparar(acervo=args.acervo,destino=args.destino),ensure_ascii=False))
