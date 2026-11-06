"""One predeclared bounded-rank experiment; original research stays immutable."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from . import qualifying_gaps as q
from . import qualifying_gaps_miami as miami
from .calibration_v2 import FEATURES_V1

PARENT = 'reports/gaps_robustos_20261102'
PROTOCOL = 'docs/experimento_gaps_robustos_20261102.md'
PREVIOUS = q.PARENT + '/run-002'
PRIMARY = 'v1_q_phase_rank'
RANKS = tuple('q_phase_rank_' + phase for phase in q.PHASES)
METHODS = q.METHODS + (PRIMARY,)


def attach_ranks(rows):
    """Average ranks in the current phase, without learned future parameters."""
    groups = defaultdict(list)
    for row in rows:
        groups[q.key(row)[:2]].append(row)
    for members in groups.values():
        for phase in q.PHASES:
            name = 'q_gap_pct_' + phase
            valid = [r[name] for r in members if r[name] is not None]
            if any(not math.isfinite(v) or v < 0 for v in valid):
                raise ValueError('invalid source gap')
            for row in members:
                value = row[name]
                if value is None or len(valid) < 2:
                    rank = None
                else:
                    # rank-1 = count strictly below + half of the other ties.
                    rank = (sum(v < value for v in valid) + (sum(v == value for v in valid)-1)/2) / (len(valid)-1)
                row['q_phase_rank_' + phase] = rank
    return rows


def load_previous(root, rows):
    """Reject cohort/feature drift, missing probabilities or changed old artefacts."""
    root = Path(root)
    manifest = json.loads((root/PREVIOUS/'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if q._sha(root/PREVIOUS/name) != digest:
            raise ValueError('previous artefact changed')
    previous = q._rows(root/PREVIOUS/'gap_features.csv')
    canonical = {q.key(r): r for r in rows}
    if len(canonical) != len(rows) or len(previous) != len(rows) or {q.key(r) for r in previous} != canonical.keys():
        raise ValueError('previous feature cohort mismatch')
    for item in previous:
        row = canonical[q.key(item)]
        for feature in q.SUPPORT + q.GAPS:
            expected = None if item[feature] == '' else float(item[feature])
            if expected != row[feature]:
                raise ValueError('previous source feature mismatch')
    predictions = []
    for p in q._rows(root/PREVIOUS/'predictions.csv'):
        k = q.key(p)
        y = None if p['podio'] == '' else int(p['podio'])
        if p['metodo'] not in q.METHODS or k not in canonical or y != canonical[k]['podio']:
            raise ValueError('previous prediction identity/target mismatch')
        predictions.append({'metodo': p['metodo'], 'temporada': k[0], 'rodada': k[1], 'piloto_id': k[2],
                            'podio': y, 'probabilidade': None if p['probabilidade'] == '' else float(p['probabilidade'])})
    return predictions


def audit_extremes(root, rows, identification, evidence):
    """Inspect all inputs; outcomes are deliberately not consulted here."""
    root = Path(root)
    original = {}
    for path in sorted((root/'data/historico').glob('*/raw/classificacao_offset_*.json')):
        if path.parent.parent.name not in {str(y) for y in range(2021, 2026)}:
            continue
        receipt_path = path.parent.parent/'proveniencia'/path.name
        receipt = json.loads(receipt_path.read_text())
        for race in json.loads(path.read_text())['MRData']['RaceTable']['Races']:
            for record in race['QualifyingResults']:
                k = (int(race['season']), int(race['round']), record['Driver']['driverId'])
                original[k] = (record, str(path.relative_to(root)), q._sha(path), str(receipt_path.relative_to(root)), receipt)
    indexed_evidence = {}
    for item in evidence['cases']:
        k = tuple(item['key']) + (item['phase'],)
        if k in indexed_evidence:
            raise ValueError('duplicate external evidence key')
        indexed_evidence[k] = item
    groups = defaultdict(list)
    for row in rows:
        for phase in q.PHASES:
            groups[(row['temporada'], phase)].append(row)
    distributions = []
    extremes = []
    for (year, phase), members in sorted(groups.items()):
        f = 'q_gap_pct_' + phase
        valid = [r[f] for r in members if r[f] is not None]
        quantiles = np.quantile(valid, [.5, .95, .99, 1]).tolist() if valid else [None]*4
        distributions.append({'year': year, 'phase': phase, 'n_rows': len(members), 'n_valid': len(valid),
                              'n_missing': len(members)-len(valid), 'n_extreme': sum(v >= 10 for v in valid),
                              **dict(zip(('median', 'p95', 'p99', 'maximum'), quantiles))})
        for row in members:
            if row[f] is None or row[f] < 10:
                continue
            k = q.key(row)
            record, path, digest, receipt_path, receipt = original[k]
            peers = {identity[2]: q.seconds(rec[0].get(phase)) for identity, rec in original.items() if identity[:2] == k[:2]}
            valid_times = {d: t for d, t in peers.items() if t is not None}
            minimum = min(valid_times.values())
            raw_time = q.seconds(record.get(phase))
            if raw_time is None or abs(100*(raw_time/minimum-1)-row[f]) > 1e-12:
                raise ValueError('extreme raw time reproduction failed')
            item = indexed_evidence.get(k+(phase,))
            if item is None or item['canonical_time'] != record[phase]:
                raise ValueError('extreme missing or inconsistent audit evidence')
            extremes.append({'temporada': k[0], 'rodada': k[1], 'piloto_id': k[2], 'phase': phase,
                             'corrida': identification[k]['corrida'], 'equipe_id_entrada': identification[k]['equipe_id_entrada'],
                             'q_position': record['position'], 'time_literal': record[phase], 'seconds': raw_time,
                             'same_phase_min_seconds': minimum, 'same_phase_min_drivers': sorted(d for d, t in valid_times.items() if t == minimum),
                             'n_valid_phase': len(valid_times), 'gap_pct': row[f], 'phase_rank': row['q_phase_rank_'+phase],
                             'source': path, 'sha256': digest, 'receipt': receipt_path, 'source_url': receipt.get('url_real') or receipt.get('url_consultada'),
                             'source_obtido_em_utc': receipt.get('obtido_em_utc'), 'evidence': item,
                             'clean_representative_pace_proven': False, 'excluded_from_fitting': False})
    if set(indexed_evidence) != {q.key(r)+(r['phase'],) for r in extremes}:
        raise ValueError('external evidence must cover exactly the input-defined extremes')
    return {'threshold_pct': 10, 'n_rows': len(rows), 'n_driver_phases': len(rows)*3,
            'n_extremes': len(extremes), 'n_gp_extreme': len({q.key(r)[:2] for r in extremes}),
            'distributions': distributions, 'cases': extremes,
            'external_evidence_used_as_predictor': False, 'excluded_observations': 0}


def experiment(rows, baseline_predictions):
    if any(r['temporada'] not in range(2021, 2026) for r in rows):
        raise ValueError('only retrospective 2021–2025 data admitted')
    predictions = list(baseline_predictions)
    fits = []
    for year in (2022, 2023, 2024, 2025):
        training = [r for r in rows if r['temporada'] < year and r['elegivel_previsao'] and r['podio'] is not None]
        population = [r for r in rows if r['temporada'] == year]
        external = [r for r in population if r['elegivel_previsao']]
        print('fit', year, PRIMARY, flush=True)
        values, fit = q.fit_candidate(training, external, FEATURES_V1 + q.SUPPORT + RANKS)
        fit.update(method=PRIMARY, year=year)
        fits.append(fit)
        available = {q.key(r): p for r, p in zip(external, values)}
        predictions.extend({'metodo': PRIMARY, 'temporada': r['temporada'], 'rodada': r['rodada'],
                            'piloto_id': r['piloto_id'], 'podio': r['podio'], 'probabilidade': available.get(q.key(r))} for r in population)
    evaluation = q.evaluate_methods([r for r in rows if r['temporada'] >= 2022], predictions, methods=METHODS)
    if any(d['status'] != 'complete' for d in evaluation['methods'].values()):
        raise ValueError('incomplete prediction cohort')
    contrasts = []
    for reference in q.METHODS:
        contrast = q.paired_interval(evaluation['gp_scores'][PRIMARY], evaluation['gp_scores'][reference])
        contrast.update(candidate=PRIMARY, reference=reference)
        contrast['favourable_folds'] = sum(f['brier'] < 0 for f in contrast.get('folds', {}).values())
        threshold = -.002 if reference in ('v1_temporal', 'q_probability') else 0
        contrast['criteria_met'] = bool(contrast['status'] == 'ok' and
            (contrast['delta_brier'] <= threshold if threshold else contrast['delta_brier'] < 0) and
            contrast.get('ci95_brier') and contrast['ci95_brier'][1] < 0 and contrast['delta_log_loss'] <= 0 and contrast['favourable_folds'] >= 3)
        contrasts.append(contrast)
    indexed = {(p['metodo'], q.key(p)): p for p in predictions}
    cases = []
    for row in rows:
        if row['temporada'] < 2022 or not any(row[g] is not None and row[g] >= 10 for g in q.GAPS):
            continue
        entry = {'temporada': row['temporada'], 'rodada': row['rodada'], 'piloto_id': row['piloto_id'], 'podio': row['podio']}
        for method in METHODS:
            p = indexed[(method, q.key(row))]['probabilidade']
            entry[method] = p
            entry[method+'_log_loss'] = None if p is None or row['podio'] is None else -math.log(p if row['podio'] else 1-p)
        cases.append(entry)
    return {'fits': fits, 'predictions': predictions, 'evaluation': evaluation, 'contrasts': contrasts,
            'extreme_predictions': cases, 'all_primary_criteria_met': all(c['criteria_met'] for c in contrasts[:3]),
            'automatic_promotion': False}


def write_reports(out, audit, result):
    for en in (False, True):
        lines = ['# '+('Extreme-gap audit and bounded ranks' if en else 'Auditoria de gaps extremos e postos limitados'), '',
                 'Created by: MBPaschoal', 'Status: executed locally; retrospective development', 'Type: research report',
                 'Date: 2026-11-02', '', '[Português](README.md) · [English](README.en.md)', '',
                 ('All {} input driver-phases reviewed; {} gaps >=10% in {} GPs. No observation deleted or corrected. Official context is audit only; numeric agreement does not certify representative clean pace.' if en else
                  'Revisadas {} observações piloto/fase; {} gaps >=10% em {} GPs. Nenhuma observação excluída ou corrigida. Contexto oficial é somente auditoria; concordância numérica não certifica ritmo limpo.').format(audit['n_driver_phases'], audit['n_extremes'], audit['n_gp_extreme']), '',
                 '| GP | Driver / Piloto | Phase / Fase | Time / Tempo | Gap % | Rank | Context / Contexto |', '|---|---|---|---|---:|---:|---|']
        for c in audit['cases']:
            e = c['evidence']
            lines.append('| {} R{} | {} | {} | {} | {:.3f} | {:.3f} | [{}]({}) |'.format(c['temporada'], c['rodada'], c['piloto_id'], c['phase'], c['time_literal'], c['gap_pct'], c['phase_rank'], e['context_en' if en else 'context_pt'], e['context_url']))
        lines += ['', '## '+('Temporal comparison' if en else 'Comparação temporal'), '',
                  '| Method / Método | N | GPs | Brier GP ↓ | Log loss GP ↓ | CITL | Slope / Inclinação | Top 3 | Podiums / Pódios |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for method, d in result['evaluation']['methods'].items():
            r = d['overall']
            lines.append('| {} | {} | {} | {:.6f} | {:.6f} | {:.6f} | {:.6f} | {:.4f} | {}/{} |'.format(method, r['n'], r['n_gp'], r['brier_mean_gp'], r['log_loss_mean_gp'], r['citl'], r['slope'], r['top3_mean'], r['complete_podiums'], r['top3_n_gp']))
        lines += ['', '| Reference / Referência | Δ Brier | CI95% / IC95% | Δ Log loss | Favourable folds / Folds favoráveis | Criteria / Critérios |', '|---|---:|---|---:|---:|---|']
        for c in result['contrasts']:
            lines.append('| {} | {:.6f} | {} | {:.6f} | {}/4 | {} |'.format(c['reference'], c['delta_brier'], c['ci95_brier'], c['delta_log_loss'], c['favourable_folds'], c['criteria_met']))
        lines += ['', ('All primary criteria met: {}. No automatic promotion.' if en else 'Todos os critérios primários atendidos: {}. Sem promoção automática.').format(result['all_primary_criteria_met']), '',
                  ('Exactly four new C=1 fits; 24 original/support/rank inputs. Competitor ranks use only the same completed qualifying phase; training medians/scales use prior seasons exclusively. Average tied ranks are bounded [0,1]; no clipping or post-result correction. This discards time distances and does not guarantee calibration. All five methods share cohorts. Raw qualifying receives ranking metrics only; the probabilistic Q reference is separate.' if en else
                   'Exatamente quatro ajustes novos C=1; 24 entradas originais/suporte/postos. Postos dos competidores usam somente a mesma fase já concluída; medianas/escalas usam apenas temporadas anteriores. Empates recebem posto médio limitado a [0,1]; sem clipping ou correção pós-resultado. A representação descarta distâncias de tempo e não garante calibração. Os cinco métodos compartilham coortes. Q bruto recebe só ranking; a referência Q probabilística é distinta.'), '',
                  ('2022–2025 were already explored and motivate this hypothesis: retrospective development, never an untouched test. No 2026 tuning. Paired CIs use 2,000 two-GP blocks within seasons, seed42, conditional on fitted predictions without refitting. Better behaviour than raw gaps alone is insufficient to replace v1. Current source captures do not certify historical availability. External audit labels were not used to mask inputs or select observations.' if en else
                   '2022–2025 já foram explorados e motivam esta hipótese: desenvolvimento retrospectivo, nunca teste intocado. Sem tuning em 2026. ICs pareados com 2.000 blocos de dois GPs dentro das temporadas, seed42, condicionais às previsões sem refit. Melhor comportamento que gaps brutos isoladamente não basta para substituir o v1. Capturas atuais não certificam disponibilidade histórica. Rótulos externos da auditoria não mascararam entradas nem selecionaram observações.'), '',
                  '[Audit](audit.json) · [Distributions](distributions.csv) · [Coverage](coverage.json) · [Features](features.csv) · [Evaluation / calibration / folds](evaluation.json) · [Predictions](predictions.csv) · [Extreme predictions](extreme_predictions.csv) · [Experiment / partitions](experiment.json) · [Frozen inputs](execution_frozen.json) · [Preservation](preservation.json) · [Manifest](manifest.json)', '']
        (out/('README.en.md' if en else 'README.md')).write_text('\n'.join(lines))


def run(root, out):
    root, out = Path(root).resolve(), Path(out).resolve()
    parent = root/PARENT
    if out.exists() or out == parent or not out.is_relative_to(parent):
        raise ValueError('output must be a new child of the experiment directory')
    baseline = json.loads((parent/'protected_before.json').read_text())
    if q.preservation(root, baseline)['status'] != 'preserved':
        raise ValueError('protected sources changed')
    previous_frozen = json.loads((root/PREVIOUS/'execution_frozen.json').read_text())
    hashes = dict(previous_frozen['hashes'])
    for name in (PROTOCOL, 'pitwall/research/robust_qualifying.py', 'tests/test_robust_qualifying.py', PARENT+'/external_audit.json', PARENT+'/protected_before.json', PREVIOUS+'/manifest.json', PREVIOUS+'/gap_features.csv', PREVIOUS+'/predictions.csv'):
        hashes[name] = q._sha(root/name)
    if any(q._sha(root/p) != digest for p, digest in hashes.items()):
        raise ValueError('previous frozen source changed')
    out.mkdir(parents=True)
    frozen = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'hashes': hashes,
              'config': {'primary': PRIMARY, 'C': 1, 'folds': [2022, 2023, 2024, 2025], 'audit_threshold_pct': 10,
                         'representation': '(average ascending rank-1)/(valid count-1), same GP/phase', 'bootstrap_reps': 2000, 'seed': 42}}
    q._json(out/'execution_frozen.json', frozen)
    try:
        with threadpool_limits(limits=1):
            rows = q.load_dataset(root)
            identification = {q.key(r): r for r in q._rows(root/'data/preparado/identificacao.csv')}
            coverage = q.local_gaps(root, rows, identification)
            coverage, _ = miami.recover(root, rows, identification, coverage)
            if coverage['status'] != 'sufficient':
                raise ValueError('coverage gate failed')
            baseline_predictions = load_previous(root, rows)
            attach_ranks(rows)
            evidence = json.loads((parent/'external_audit.json').read_text())
            audit = audit_extremes(root, rows, identification, evidence)
            q._json(out/'audit.json', audit)
            q._csv(out/'distributions.csv', audit['distributions'])
            q._json(out/'coverage.json', {k: v for k, v in coverage.items() if k != 'features'})
            q._csv(out/'features.csv', [{'temporada': r['temporada'], 'rodada': r['rodada'], 'piloto_id': r['piloto_id'], **{f: r[f] for f in q.SUPPORT+q.GAPS+RANKS}} for r in rows])
            result = experiment(rows, baseline_predictions)
            q._json(out/'experiment.json', result)
            q._json(out/'evaluation.json', result['evaluation'])
            q._csv(out/'predictions.csv', result['predictions'])
            q._csv(out/'extreme_predictions.csv', result['extreme_predictions'])
            write_reports(out, audit, result)
        after = q.preservation(root, baseline)
        q._json(out/'preservation.json', after)
        if after['status'] != 'preserved' or any(q._sha(root/p) != digest for p, digest in hashes.items()):
            raise ValueError('protected inputs/code changed during execution')
        manifest = {'status': 'completed', 'automatic_promotion': False, 'protected_files': after['checked_files'],
                    'all_primary_criteria_met': result['all_primary_criteria_met'], 'files': {p.name: q._sha(p) for p in sorted(out.iterdir()) if p.is_file()}}
        q._json(out/'manifest.json', manifest)
        return manifest
    except Exception as error:
        q._json(out/'failure.json', {'error': str(error), 'preservation': q.preservation(root, baseline)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.destination or args.root/PARENT/'run-001')))


if __name__ == '__main__':
    main()
