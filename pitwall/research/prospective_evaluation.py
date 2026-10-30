"""Evaluate already recorded predictions; never infer or revise probabilities."""

def prospective_races(package):
    if package.get('temporada') != 2026:
        return []
    rows = []
    for race in package['corridas']:
        if race.get('estado_previsao') != 'previsao_registrada' or race.get('resultado_posterior_validado') is not True or race.get('avaliavel_ranking') is not True:
            continue
        if any((type(race.get(key)) is not int or not 0 <= race[key] <= 3 for key in ('acertos_modelo', 'acertos_classificacao'))):
            raise ValueError('Invalid recorded-prediction evaluation')
        rows.append(dict(rodada=race['rodada'], corrida=race['corrida'], modelo=race['acertos_modelo'], classificacao=race['acertos_classificacao']))
    return sorted(rows, key=lambda r: r['rodada'])
