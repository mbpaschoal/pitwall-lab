"""Read-only, event-gated access to the all-car descriptive snapshot."""
from pathlib import Path
import json
import math
from pitwall.research.car_comparison import TEAMS, digest

ASSET='frontend_assets/car_comparison_2026.json'


class CarDataError(ValueError):
    pass


def load(root):
    try:
        asset=json.loads((Path(root)/ASSET).read_text(encoding='utf-8'))
    except (OSError,ValueError) as error:
        raise CarDataError('Dados dos carros indisponíveis ou inválidos.') from error
    try:
        return validate(asset)
    except CarDataError:
        raise
    except (KeyError,TypeError,ValueError,AttributeError) as error:
        raise CarDataError('Dados dos carros indisponíveis ou inválidos.') from error


def validate(asset):
    if (not isinstance(asset,dict) or asset.get('schema')!='pitwall-car-comparison-v1' or asset.get('season')!=2026
            or asset.get('forecast_input') is not False or asset.get('retrospective') is not True
            or asset.get('content_sha256')!=digest(asset)):
        raise CarDataError('A integridade dos dados dos carros não pôde ser validada.')
    seen=set()
    for event in asset.get('events',[]):
        key=(event.get('season'),event.get('round'))
        if key in seen or key[0]!=2026 or not isinstance(key[1],int):
            raise CarDataError('Identidade de evento incompatível nos dados dos carros.')
        seen.add(key)
        teams=event.get('teams',[])
        if len(teams)!=11 or {x.get('team_id') for x in teams}!=set(TEAMS):
            raise CarDataError('A cobertura das equipes está incompleta.')
        for team in teams:
            for variant in ('q1','q1_no_flags'):
                metric=team[variant];value=metric['gap_percent']
                if (value is not None and (not isinstance(value,(int,float)) or not math.isfinite(value))) or (value is not None and metric['eligible_drivers']!=2):
                    raise CarDataError('A amostra do comparativo dos carros é incompatível.')
    return asset


def for_event(asset,year,round_,circuit_id=None):
    found=[e for e in asset['events'] if e['season']==year and e['round']==round_]
    if len(found)!=1:return None
    event=found[0]
    if circuit_id is not None and event['circuit_id']!=circuit_id:
        raise CarDataError('O circuito selecionado não corresponde aos dados dos carros.')
    return event


def team_rows(event,no_flags=False):
    key='q1_no_flags' if no_flags else 'q1'
    return sorted(event['teams'],key=lambda t:(t[key]['gap_percent'] is None,t[key]['gap_percent'] or 0,t['name']))
