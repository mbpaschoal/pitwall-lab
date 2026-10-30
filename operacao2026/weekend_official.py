"""Round-specific official standings; never reconstructed from partial results."""

def standings(client, event, teams=False):
    endpoint = 'constructorstandings' if teams else 'driverstandings'
    field = 'ConstructorStandings' if teams else 'DriverStandings'
    rows = []
    offset = 0
    total = None
    while True:
        url = 'https://api.jolpi.ca/ergast/f1/{}/{}/{}/?limit=100&offset={}'.format(event['temporada'], event['rodada'], endpoint, offset)
        payload = client.capture('jolpica', endpoint, 'official/{}-{}.json'.format(endpoint, offset), url)
        if not isinstance(payload, dict):
            return dict(disponivel=False, classificacao=[], motivo='fonte_indisponivel')
        meta = payload['MRData']
        expected = int(meta['total'])
        if int(meta['offset']) != offset or expected > 10000 or expected < 0 or (total is not None and expected != total):
            raise ValueError('Standings pagination mismatch')
        total = expected
        if total == 0:
            return dict(disponivel=False, classificacao=[], motivo='rodada_ainda_nao_publicada')
        lists = meta['StandingsTable']['StandingsLists']
        if len(lists) != 1 or int(lists[0]['season']) != event['temporada'] or int(lists[0]['round']) != event['rodada']:
            raise ValueError('Standings belong to another round')
        page = lists[0][field]
        if not page or len(page) > 100 or len(rows) + len(page) > total:
            raise ValueError('Incomplete standings page')
        rows.extend(page)
        offset += len(page)
        if offset == total:
            break
    normalized = []
    seen = set()
    for row in rows:
        entity = row['Constructor' if teams else 'Driver']
        key = entity['constructorId' if teams else 'driverId']
        if key in seen:
            raise ValueError('Duplicate standings entity')
        seen.add(key)
        value = dict(posicao=int(row['position']) if row.get('position') else None, pontos=float(row['points']), vitorias=int(row['wins']))
        if teams:
            value.update(equipe_id=key, equipe=entity['name'])
        else:
            value.update(piloto_id=key, piloto=entity['givenName'] + ' ' + entity['familyName'], nacionalidade=entity.get('nationality'), equipe=' / '.join((t['name'] for t in row['Constructors'])), equipe_ids=[t['constructorId'] for t in row['Constructors']])
        normalized.append(value)
    return dict(disponivel=True, classificacao=normalized, rodada_referencia=event['rodada'], escopo='Campeonato oficial da rodada', fonte='Jolpica-F1', obtido_em_utc=client.manifest['fontes'][-1]['obtido_em_utc'], url=url)
