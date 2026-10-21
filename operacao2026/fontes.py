"""Coleta sequencial e fotografia bruta exclusiva para 2026."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import fcntl
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

BASE = 'https://api.jolpi.ca/ergast/f1/2026/'
LIMITE, INTERVALO_MINIMO, TENTATIVAS = 100, 8.0, 2
UA = 'PitwallLab/operacao-2026 (educational portfolio; sequential cache client)'
_ENDPOINTS = frozenset(('calendario', 'resultados', 'classificacao'))
_SAFE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
_HEX = re.compile(r'^[0-9a-f]{64}$')
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def _retry_after(headers, now=None):
    value = headers.get('Retry-After') if headers else None
    if not value:
        return None
    try:
        delay = float(value)
        if not math.isfinite(delay) or delay < 0:
            raise ValueError
        return delay
    except (TypeError, ValueError):
        try:
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return max(0.0, (deadline - (now or datetime.now(timezone.utc))).total_seconds())
        except (TypeError, ValueError, IndexError) as error:
            raise RuntimeError('Retry-After inválido: {!r}'.format(value)) from error


class ClienteHTTP:
    """Relógio por instância: não há espaçamento mutável global para testes."""
    def __init__(self, opener=urlopen, sleeper=time.sleep, clock=time.monotonic, utc_clock=None):
        self.opener, self.sleeper, self.clock = opener, sleeper, clock
        self.utc_clock = utc_clock or (lambda: datetime.now(timezone.utc))
        self.last, self.logical = None, None

    def _start(self):
        now = self.clock(); logical = now if self.logical is None else max(now, self.logical)
        if self.last is not None:
            wait = max(0.0, INTERVALO_MINIMO - (logical - self.last))
            if wait:
                self.sleeper(wait); logical += wait
        self.last = self.logical = logical

    def buscar(self, url, offset):
        params = {'limit': LIMITE, 'offset': offset}
        full = url + ('&' if '?' in url else '?') + urlencode(params)
        for attempt in range(TENTATIVAS):
            self._start(); response = None
            try:
                req = Request(full, headers={'User-Agent': UA, 'Accept': 'application/json'})
                response = self.opener(req, timeout=30)
                return {'bytes': response.read(), 'status': getattr(response, 'status', 200),
                        'url_solicitada': full, 'url_real': getattr(response, 'url', full),
                        'obtido_em_utc': self.utc_clock().isoformat().replace('+00:00', 'Z'),
                        'parametros': params, 'origem': 'rede'}
            except Exception as error:
                code = getattr(error, 'code', None)
                if code in (429, 503):
                    wait = _retry_after(getattr(error, 'headers', None), self.utc_clock())
                    if wait is not None:
                        if wait > 120:
                            raise RuntimeError('Retry-After acima de 120 segundos; coleta interrompida.') from error
                        self.sleeper(wait); self.logical = (self.logical or self.clock()) + wait
                if code not in (429, 500, 502, 503, 504) or attempt + 1 == TENTATIVAS:
                    message = 'HTTP {} ao consultar {}'.format(code, full) if code else 'Falha de rede ao consultar {}'.format(full)
                    raise RuntimeError(message) from error
            finally:
                if response is not None:
                    response.close()
        raise AssertionError('retry esgotado')


def buscar_pagina(url, offset, opener=urlopen, sleeper=time.sleep, clock=time.monotonic, contexto=None):
    return (contexto or ClienteHTTP(opener, sleeper, clock)).buscar(url, offset)


def _int(value, message):
    if isinstance(value, bool):
        raise ValueError(message)
    try: result = int(value)
    except (TypeError, ValueError, OverflowError) as error: raise ValueError(message) from error
    if not isinstance(value, int) and str(result) != str(value): raise ValueError(message)
    return result


def _field(endpoint): return {'resultados': 'Results', 'classificacao': 'QualifyingResults'}.get(endpoint)


def _race_table(payload):
    try:
        table = payload['MRData']['RaceTable']
        if str(table['season']) != '2026' or not isinstance(table['Races'], list): raise ValueError
        return table
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Envelope Jolpica inválido para temporada 2026.') from error


def _race_key(race):
    try:
        date, hour = race['date'], race['time']
        datetime.strptime(date + 'T' + hour, '%Y-%m-%dT%H:%M:%SZ')
        circuit = race['Circuit']['circuitId']; key = (str(race['season']), str(race['round']))
        if key[0] != '2026' or not isinstance(circuit, str) or not circuit: raise ValueError
        return key, circuit
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Corrida/data/hora UTC inválida.') from error


def validar_pagina(raw, endpoint, expected_round=None, expected_event=None):
    if endpoint not in _ENDPOINTS: raise ValueError('Endpoint inválido.')
    try:
        payload = json.loads(raw.decode('utf-8')); meta = payload['MRData']
        offset, limit, total = (_int(meta['offset'], 'Metadados de paginação inválidos.'), _int(meta['limit'], 'Metadados de paginação inválidos.'), _int(meta['total'], 'Metadados de paginação inválidos.'))
    except (UnicodeDecodeError, ValueError, TypeError, KeyError) as error:
        raise ValueError('Página não é JSON Jolpica paginado válido.') from error
    if offset < 0 or limit != LIMITE or total < 0: raise ValueError('Metadados de paginação inválidos.')
    races, seen, field = _race_table(payload)['Races'], set(), _field(endpoint)
    for race in races:
        key, circuit = _race_key(race)
        if key in seen or (expected_round is not None and key[1] != str(expected_round)): raise ValueError('Identidade de corrida inválida ou duplicada.')
        if expected_event and (key != (str(expected_event['season']), str(expected_event['round'])) or race['date'] != expected_event['date'] or circuit != expected_event['Circuit']['circuitId']): raise ValueError('Envelope de GP diverge do calendário.')
        seen.add(key)
        if not field: continue
        entries = race.get(field)
        if not isinstance(entries, list): raise ValueError('Registros {} inválidos.'.format(field))
        drivers = set()
        for entry in entries:
            try: driver, team = entry['Driver']['driverId'], entry['Constructor']['constructorId']
            except (KeyError, TypeError) as error: raise ValueError('ID de piloto/equipe inválido.') from error
            if not isinstance(driver, str) or not _ID.fullmatch(driver) or not isinstance(team, str) or not _ID.fullmatch(team) or driver in drivers: raise ValueError('piloto duplicado ou ID inválido.')
            drivers.add(driver)
            if field == 'Results':
                try:
                    position, points = _int(entry['position'], 'Posição/pontos de resultado inválidos.'), float(entry['points'])
                    if position <= 0 or points < 0 or not math.isfinite(points): raise ValueError
                except (KeyError, TypeError, ValueError, OverflowError) as error: raise ValueError('Posição/pontos de resultado inválidos.') from error
            elif entry.get('position') not in (None, '') and _int(entry['position'], 'Posição de classificação inválida.') <= 0:
                raise ValueError('Posição de classificação inválida.')
    count = sum(len(race[field]) for race in races) if field else len(races)
    if offset > total or count != min(limit, total - offset):
        raise ValueError('Paginação incompleta ou quantidade de registros incoerente com limit/offset/total.')
    return payload, total, offset, len(races)


def _identidade_fragmento(race, field):
    """Compara todo o envelope do GP, exceto os participantes desta página."""
    return _json_bytes({key: value for key, value in race.items() if key != field})


def paginas_completas(fetch, endpoint, expected_round=None, expected_event=None):
    pages=[]; races_seen=set(); drivers=set(); positions=set(); entries=0; offset=0; total=None; field=_field(endpoint); event_identity=None
    while total is None or offset < total:
        item=fetch(offset); payload, page_total, page_offset, _ = validar_pagina(item['bytes'], endpoint, expected_round, expected_event)
        if page_offset != offset or (total is not None and page_total != total): raise ValueError('Paginação incompleta ou total divergente.')
        total=page_total; races=payload['MRData']['RaceTable']['Races']
        if not races and total: raise ValueError('Página vazia antes do total.')
        for race in races:
            key=(race['season'], race['round'])
            if field is None:
                if key in races_seen: raise ValueError('Corrida duplicada entre páginas.')
                races_seen.add(key)
            else:
                identity=_identidade_fragmento(race, field)
                if event_identity is None: event_identity=identity
                elif identity != event_identity: raise ValueError('Envelope de GP diverge entre páginas.')
            for entry in race.get(field, []) if field else []:
                driver=entry['Driver']['driverId']
                if driver in drivers: raise ValueError('piloto duplicado entre páginas.')
                drivers.add(driver); entries += 1
                if field == 'Results':
                    pos=_int(entry['position'], 'Posição/pontos de resultado inválidos.')
                    if pos in positions: raise ValueError('posição de resultado duplicada entre páginas.')
                    positions.add(pos)
        pages.append(item); offset += LIMITE
    if (field and entries != total) or (not field and len(races_seen) != total): raise ValueError('Paginação de registros incompleta.')
    return pages


def _sid(value):
    if not isinstance(value, str) or not _SAFE.match(value) or '..' in value: raise ValueError('snapshot_id inseguro.')
    return value


def _path(base, rel):
    pure=PurePosixPath(rel) if isinstance(rel, str) else None
    if not pure or pure.is_absolute() or pure.parts[:1] != ('raw',) or len(pure.parts) != 2 or '..' in pure.parts: raise ValueError('Caminho raw inseguro.')
    path=base.joinpath(*pure.parts); current=base
    for part in pure.parts:
        current=current / part
        if current.exists() and current.is_symlink(): raise ValueError('Symlink não permitido no snapshot.')
    return path


def _regular(path): return os.path.isfile(path) and not path.is_symlink()


def _entry(entry):
    needed=('arquivo','endpoint','sha256','parametros','status','url_solicitada','url_real','obtido_em_utc','origem')
    if not isinstance(entry, dict) or any(key not in entry for key in needed) or entry['endpoint'] not in _ENDPOINTS or not isinstance(entry['sha256'], str) or not _HEX.match(entry['sha256']): raise ValueError('Fonte/hash/tipo inválido no índice.')
    if not isinstance(entry['parametros'], dict) or _int(entry['parametros'].get('offset'), 'Offset inválido.') < 0 or isinstance(entry['status'], bool) or not isinstance(entry['status'], int): raise ValueError('Entrada de índice inválida.')


def ler_indice(root, snapshot_id):
    sid=_sid(snapshot_id); base=Path(root)/sid; indice=base/'indice.json'
    if base.is_symlink() or not base.is_dir() or not _regular(indice): raise ValueError('Índice inexistente ou inseguro.')
    try: index=json.loads(indice.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, ValueError) as error: raise ValueError('Índice inválido.') from error
    if not isinstance(index, dict) or index.get('versao') != 1 or index.get('snapshot_id') != sid or not isinstance(index.get('fontes'), list): raise ValueError('Índice inválido.')
    files=set()
    for source in index['fontes']:
        _entry(source); _path(base, source['arquivo'])
        if source['arquivo'] in files: raise ValueError('Arquivo duplicado no índice.')
        files.add(source['arquivo'])
    return index


def ler_snapshot(root, snapshot_id, carregar=True, endpoints=None, rodadas=None):
    index=ler_indice(root, snapshot_id); wanted=None if endpoints is None else set(endpoints)
    if wanted is not None and not wanted <= _ENDPOINTS: raise ValueError('Endpoint solicitado inválido.')
    rounds=None if rodadas is None else {str(round_) for round_ in rodadas}
    if rounds is not None and any(not round_ for round_ in rounds): raise ValueError('Rodadas solicitadas inválidas.')
    base=Path(root)/snapshot_id;    selected=[]
    for source in index['fontes']:
        if wanted is not None and source['endpoint'] not in wanted: continue
        if rounds is not None and source.get('rodada') not in rounds: continue
        selected.append(source)
    out={}
    for source in selected:
        path=_path(base, source['arquivo'])
        if carregar:
            if not _regular(path): raise ValueError('Raw inexistente ou inseguro: {}'.format(source['arquivo']))
            raw=path.read_bytes()
            if sha256(raw).hexdigest() != source['sha256']: raise ValueError('Hash divergente no snapshot: {}'.format(source['arquivo']))
            try: value=json.loads(raw.decode('utf-8'))
            except (UnicodeDecodeError, ValueError) as error: raise ValueError('Raw JSON inválido: {}'.format(source['arquivo'])) from error
        else: value=path
        out.setdefault(source['endpoint'], []).append((source, value))
    if carregar:
        _validar_selecao_snapshot(out)
    return index, out


def _validar_selecao_snapshot(pages):
    """Revalida o conjunto selecionado sem tocar raws fora do filtro."""
    groups = {}
    for endpoint, entries in pages.items():
        for source, payload in entries:
            raw = _json_bytes(payload)
            expected = source.get('rodada')
            checked, total, offset, _ = validar_pagina(raw, endpoint, expected)
            if _int(source['parametros'].get('offset'), 'Offset inválido.') != offset:
                raise ValueError('Offset do índice diverge do raw.')
            if 'limit' in source['parametros'] and _int(source['parametros']['limit'], 'Limite inválido.') != LIMITE:
                raise ValueError('Limite do índice diverge do raw.')
            groups.setdefault((endpoint, expected), []).append((source, checked, total, offset))
    for (endpoint, expected), items in groups.items():
        total = items[0][2]
        offsets = [item[3] for item in items]
        if any(item[2] != total for item in items) or sorted(offsets) != list(range(0, total if total else 1, LIMITE)):
            raise ValueError('Paginação incompleta ou total divergente no snapshot.')
        field = _field(endpoint); records = 0; ids = set(); positions = set(); races = set(); event_identity = None
        for _, payload, _, _ in sorted(items, key=lambda item: item[3]):
            for race in _race_table(payload)['Races']:
                key, _ = _race_key(race)
                if field is None:
                    if key in races: raise ValueError('Corrida duplicada entre páginas do snapshot.')
                    races.add(key); records += 1; continue
                identity = _identidade_fragmento(race, field)
                if event_identity is None:
                    event_identity = identity
                elif identity != event_identity:
                    raise ValueError('Envelope de GP diverge entre páginas do snapshot.')
                for entry in race[field]:
                    driver = entry['Driver']['driverId']
                    if driver in ids: raise ValueError('Piloto duplicado entre páginas do snapshot.')
                    ids.add(driver); records += 1
                    if field == 'Results':
                        position = _int(entry['position'], 'Posição/pontos de resultado inválidos.')
                        if position in positions: raise ValueError('Posição de resultado duplicada entre páginas do snapshot.')
                        positions.add(position)
        if records != total:
            raise ValueError('Paginação de registros incompleta no snapshot.')


class _Writer:
    def __init__(self, root, snapshot_id=None):
        sid=_sid(snapshot_id) if snapshot_id else datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + str(uuid.uuid4())
        self.dest=Path(root)/sid; self.dest.parent.mkdir(parents=True, exist_ok=True); self.dest.mkdir()
        self.index={'versao':1,'snapshot_id':sid,'criado_em_utc':utc_now(),'fontes':[]}
    def add(self, endpoint, page, round_=None):
        offset=_int(page['parametros']['offset'], 'Offset inválido.'); suffix='' if round_ is None else '_' + str(round_)
        rel='raw/{}{}_offset_{:04d}.json'.format(endpoint, suffix, offset); path=_path(self.dest, rel); path.parent.mkdir(exist_ok=True)
        if path.exists(): raise FileExistsError('Destino já existe e foi preservado: {}'.format(path))
        raw=page['bytes']; path.write_bytes(raw)
        source={key:page[key] for key in ('url_solicitada','url_real','parametros','obtido_em_utc','status','origem')}; source.update({'arquivo':rel,'endpoint':endpoint,'sha256':sha256(raw).hexdigest()})
        if round_ is not None: source['rodada']=str(round_)
        if page.get('origem_cache'): source['origem_cache']=page['origem_cache']
        self.index['fontes'].append(source)
    def done(self, quality=None):
        if quality: self.index['qualidade']=quality
        (self.dest/'indice.json').write_bytes(_json_bytes(self.index)); return self.dest


def gravar_snapshot(root, snapshot_id, pages_by_name):
    writer=_Writer(root, snapshot_id)
    for endpoint, pages in sorted(pages_by_name.items()):
        for page in pages: writer.add(endpoint, page, page.get('rodada'))
    return writer.done()


def discover_event(calendar_races, circuit_id):
    found=[race for race in calendar_races if race.get('Circuit',{}).get('circuitId') == circuit_id]
    if len(found) != 1: raise ValueError('Circuito {} deve aparecer exatamente uma vez no calendário.'.format(circuit_id))
    return found[0]


def _download(writer, endpoint, url, fetch, round_=None, event=None):
    saved=[]
    def one(offset):
        # ``fetch`` representa uma consulta nova; só o caminho ``_cached``
        # pode gravar proveniência de cache no snapshot novo.
        page=dict(fetch(url, offset)); page['origem']='rede'
        writer.add(endpoint, page, round_); saved.append(page); return page
    paginas_completas(one, endpoint, round_, event); return saved


def _cached(root, event):
    for child in Path(root).iterdir() if Path(root).exists() else ():
        if not child.is_dir() or child.is_symlink(): continue
        try: index, pages=ler_snapshot(root, child.name, endpoints={'resultados'})
        except ValueError: continue
        selected=[(source, payload) for source, payload in pages.get('resultados', []) if source.get('rodada') in (None, str(event['round']))]
        if not selected: continue
        items=[]
        for source, payload in selected:
            raw=_json_bytes(payload) if False else _path(child, source['arquivo']).read_bytes()
            items.append(dict(source, bytes=raw, origem='cache', origem_cache=source['origem']))
        try:
            pages_by_offset={item['parametros']['offset']:item for item in items}
            pages=paginas_completas(lambda offset: pages_by_offset[offset], 'resultados', event['round'], event)
            count=sum(len(race.get('Results', [])) for page in pages for race in json.loads(page['bytes'].decode('utf-8'))['MRData']['RaceTable']['Races'])
            if count == 0:
                return None
            return pages
        except (KeyError, ValueError):
            raise ValueError('Cache de resultados inválido; coleta interrompida.')
    return None


@contextmanager
def _lock(root):
    Path(root).mkdir(parents=True, exist_ok=True)
    with open(str(Path(root)/'.coletor.lock'), 'a+') as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def coletar_snapshot(root, snapshot_id=None, atualizar=False, circuitos=None, agora=None, fetch=None):
    agora=agora or datetime.now(timezone.utc)
    if agora.tzinfo is None: raise ValueError('Corte de coleta deve estar em UTC.')
    circuits=tuple(('americas','marina_bay') if circuitos is None else circuitos)
    if any(not isinstance(value,str) or not value for value in circuits): raise ValueError('Circuitos inválidos.')
    with _lock(root):
        writer=_Writer(root, snapshot_id); client=ClienteHTTP(); request=fetch or (lambda url, offset: client.buscar(url, offset))
        calendar=_download(writer, 'calendario', BASE, request)
        races=[race for page in calendar for race in json.loads(page['bytes'].decode('utf-8'))['MRData']['RaceTable']['Races']]
        quality={'resultados_disponiveis':[],'lacunas_resultados':[],'futuros':[]}
        for event in races:
            if datetime.strptime(event['date'], '%Y-%m-%d').date() + timedelta(days=1) > agora.date(): quality['futuros'].append(event['round']); continue
            pages=None if atualizar else _cached(root, event)
            if pages is None: pages=_download(writer, 'resultados', BASE + str(event['round']) + '/results/', request, event['round'], event)
            else:
                for page in pages: writer.add('resultados', page, event['round'])
            count=sum(len(r.get('Results',[])) for page in pages for r in json.loads(page['bytes'].decode('utf-8'))['MRData']['RaceTable']['Races'])
            (quality['resultados_disponiveis'] if count else quality['lacunas_resultados']).append(event['round'])
        for circuit in circuits:
            event=discover_event(races, circuit)
            _download(writer, 'classificacao', BASE + str(event['round']) + '/qualifying/', request, event['round'], event)
        return writer.done(quality)
