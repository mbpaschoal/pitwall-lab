"""Regressões R2 sintéticas do caminho prospectivo; sem rede ou dados reais."""
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import operar_2026 as cli
import preparar_dashboard_race_weekend as preparar
import race_weekend_dados
import registro_emissoes
from operacao2026 import fontes, previsao
from streamlit.testing.v1 import AppTest


SCRATCH = Path(os.environ.get('TMPDIR') or tempfile.gettempdir()).resolve()
RAIZ = Path(__file__).resolve().parents[1]
RACE_START = datetime(2026, 10, 25, 20, tzinfo=timezone.utc)
FAKE_GIT = {'commit': 'synthetic-not-a-commit', 'componentes_rastreados': True,
            'componentes_limpos': True, 'sha256': {}}


def corrida(year, round_, date_, circuit='legacy', qdate=None):
    return {'season': str(year), 'round': str(round_), 'raceName': 'SYNTHETIC',
            'date': date_, 'time': '20:00:00Z',
            'Circuit': {'circuitId': circuit},
            'Qualifying': {'date': qdate or date_, 'time': '21:00:00Z'}}


def resultado(driver='a', team='team', position=1, points=25):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': team},
            'position': str(position), 'points': str(points), 'status': 'Finished'}


def quali(driver='a', team='team', position=1):
    return {'Driver': {'driverId': driver, 'givenName': driver, 'familyName': 'Synthetic'},
            'Constructor': {'constructorId': team}, 'position': str(position)}


def raw_page(races, endpoint, offset=0, total=None):
    field = {'classificacao': 'QualifyingResults', 'resultados': 'Results'}.get(endpoint)
    count = sum(len(race.get(field, [])) for race in races) if field else len(races)
    return json.dumps({'MRData': {'limit': '100', 'offset': str(offset), 'total': str(count if total is None else total),
                                  'RaceTable': {'season': '2026', 'Races': races}}}).encode('utf-8')


def source(raw, endpoint, round_=None, got='2026-10-24T22:01:00Z', offset=0):
    item = {'bytes': raw, 'parametros': {'offset': offset, 'limit': 100}, 'status': 200,
            'url_solicitada': 'https://fixture.invalid/{}'.format(endpoint),
            'url_real': 'https://fixture.invalid/{}'.format(endpoint),
            'obtido_em_utc': got, 'origem': 'fixture'}
    if round_ is not None:
        item['rodada'] = str(round_)
    return item


class Operacao2026R2Test(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.temp.name)
        self.snapshots = self.root / 'snapshots'
        self.emissions = self.root / 'emissions'
        self.history = self.root / 'data/historico'

    def tearDown(self):
        self.temp.cleanup()

    def _historico_real(self, unknown_2024=False):
        for year in range(2021, 2026):
            event = corrida(year, 1, '{}-03-01'.format(year))
            calendar = raw_page([event], 'calendario')
            team = 'team' if year >= 2024 else 'old_team'
            results = raw_page([dict(event, Results=[resultado('a', team),
                                                     resultado('legacy_{}'.format(year), team, 2, 18)])],
                               'resultados')
            raw = self.history / str(year) / 'raw'
            raw.mkdir(parents=True)
            (raw / 'calendar.json').write_bytes(calendar)
            (raw / 'results.json').write_bytes(results)
            got = 'desconhecida' if unknown_2024 and year == 2024 else '2026-10-17T12:00:00Z'
            provenance = []
            for endpoint, name, payload in (('calendario', 'raw/calendar.json', calendar),
                                            ('resultados', 'raw/results.json', results)):
                provenance.append({'endpoint': endpoint, 'arquivo': name,
                                   'sha256': hashlib.sha256(payload).hexdigest(),
                                   'obtido_em_utc': got})
            (raw.parent / 'manifesto.json').write_text(json.dumps({'proveniencia': provenance}))

    def _snapshot(self, name, include_2026_history):
        target = corrida(2026, 18, '2026-10-25', 'americas', qdate='2026-10-24')
        races = [target]
        qualificacao = [quali('piloto_{:03d}'.format(item), 'team', item + 1) for item in range(101)]
        # Ambas as páginas são gravadas fora de ordem para provar a ordenação por offset.
        pages = {'calendario': [], 'classificacao': [
            source(raw_page([dict(target, QualifyingResults=qualificacao[100:])], 'classificacao', 100, 101),
                   'classificacao', 18, '2026-10-24T22:02:00Z', 100),
            source(raw_page([dict(target, QualifyingResults=qualificacao[:100])], 'classificacao', 0, 101),
                   'classificacao', 18, '2026-10-24T22:01:00Z', 0),
        ]}
        if include_2026_history:
            previous = [corrida(2026, round_, '2026-0{}-0{}'.format(round_ + 1, round_), 'prior')
                        for round_ in range(1, 6)]
            races = previous + races
            pages['resultados'] = [
                source(raw_page([dict(event, Results=[resultado()])], 'resultados'), 'resultados', event['round'])
                for event in previous]
        pages['calendario'] = [source(raw_page(races, 'calendario'), 'calendario')]
        fontes.gravar_snapshot(self.snapshots, name, pages)

    def _args(self, snapshot, emission_id):
        return ['emitir', '--snapshot', snapshot, '--id', emission_id,
                '--sessao-encerrada-em', '2026-10-24T22:00:00Z',
                '--fonte-encerramento', 'https://fixture.invalid/q-finished',
                '--corte', '2026-10-24T22:30:00Z']

    def _run_cli(self, snapshot, emission_id, clock=None, phase=None):
        clock = clock or [RACE_START - timedelta(seconds=1)]
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock[0]
        original_json, original_open, original_replace = previsao._bytes_json, Path.open, previsao.os.replace
        triggered = [False]
        def advance():
            triggered[0] = True
            clock[0] = RACE_START.replace(second=1)
        def serialize(value):
            advance()
            return original_json(value)
        def writing(path, *args, **kwargs):
            handle = original_open(path, *args, **kwargs)
            if path.name == 'probabilidades.csv':
                advance()
            return handle
        def replacing(source_path, destination):
            value = original_replace(source_path, destination)
            advance()
            return value
        output = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(cli, 'ROOT', self.root))
            stack.enter_context(patch.object(cli, 'SNAPSHOTS', self.snapshots))
            stack.enter_context(patch.object(cli, 'EMISSOES', self.emissions))
            stack.enter_context(patch.object(cli, 'datetime', Clock))
            stack.enter_context(patch.object(previsao, 'codigo_estado', return_value=FAKE_GIT))
            stack.enter_context(patch.object(previsao, 'carregar_modelo', return_value={'hashes': {'modelo': 'synthetic-model', 'metadados': 'synthetic-meta', 'esquema': 'synthetic-schema'}}))
            stack.enter_context(patch.object(previsao, 'inferir', side_effect=lambda model, rows: rows))
            if phase == 'serializacao':
                stack.enter_context(patch.object(previsao, '_bytes_json', serialize))
            elif phase == 'escrita':
                stack.enter_context(patch.object(Path, 'open', writing))
            elif phase == 'replace':
                stack.enter_context(patch.object(previsao.os, 'replace', replacing))
            with redirect_stdout(output), redirect_stderr(output):
                code = cli.main(self._args(snapshot, emission_id))
        return code, output.getvalue(), triggered[0], clock

    def test_cli_admite_historico_antigo_e_exclui_2024_desconhecido_sem_mudar_matriz(self):
        self._historico_real(unknown_2024=True)
        self._snapshot('completo', include_2026_history=True)
        code, output, _, _ = self._run_cli('completo', 'legacy-excluido')
        self.assertEqual(code, 0, output)
        manifest = json.loads((self.emissions / 'legacy-excluido/manifesto.json').read_text())
        admitted = manifest['fontes_historicas_admitidas']
        excluded = manifest['fontes_historicas_excluidas']
        self.assertFalse(any(item['obtido_em_utc'] == 'desconhecida' for item in admitted))
        unknown = [item for item in excluded if item['obtido_em_utc'] == 'desconhecida']
        self.assertEqual(len(unknown), 2)
        self.assertTrue(all(item['motivo_exclusao'] == 'ausência de contribuição às janelas v1' for item in unknown))
        self.assertTrue(all(item['origem'] == 'historico_congelado' and len(item['sha256']) == 64
                            and 'eventos' in item for item in manifest['fontes_historicas_abertas']))
        historic = json.loads((self.emissions / 'legacy-excluido/historicos.json').read_text())
        self.assertGreater(len(historic['resultados_lidos']), len(historic['resultados_fornecidos']))
        self.assertEqual(len(historic['resultados_fornecidos']), 5)

    def test_cli_bloqueia_fonte_2024_desconhecida_quando_janela_a_exige(self):
        self._historico_real(unknown_2024=True)
        self._snapshot('legado-necessario', include_2026_history=False)
        code, output, _, _ = self._run_cli('legado-necessario', 'legacy-bloqueado')
        self.assertEqual(code, 1)
        self.assertIn('Fonte histórica admitida sem obtenção UTC válida', output)
        self.assertFalse((self.emissions / 'legacy-bloqueado').exists())

    def test_cli_produz_corte_temporal_derivado_consumivel_pelo_registro(self):
        self._historico_real()
        self._snapshot('contrato-temporal', include_2026_history=True)
        code, output, _, _ = self._run_cli('contrato-temporal', 'prospectivo-contrato')
        self.assertEqual(code, 0, output)
        manifesto = json.loads((self.emissions / 'prospectivo-contrato' / 'manifesto.json').read_text())
        self.assertEqual(manifesto['source_snapshots'], ['contrato-temporal'])
        self.assertEqual(manifesto['corte_temporal'], {
            'qualificacao_inicio_utc': '2026-10-24T21:00:00Z',
            'qualificacao_encerrada_em_utc': '2026-10-24T22:00:00Z',
            'qualificacao_disponivel_em_utc': '2026-10-24T22:02:00Z',
            'corte_utc': '2026-10-24T22:30:00Z',
            'corrida_programada_em_utc': '2026-10-25T20:00:00Z',
            'resultado_alvo_incluido': False,
        })
        destino_snapshot = self.root / 'data' / 'operacao_2026' / 'snapshots'
        destino_snapshot.mkdir(parents=True)
        # A é a contraprova R4: a base e a emissão contêm a mesma Q paginada,
        # em offsets fora de ordem no índice. A seleção da emissão não pode falhar
        # nem usar a Q-base por acidente.
        shutil.copytree(self.snapshots / 'contrato-temporal', destino_snapshot / 'base-paginada')
        indice_base = destino_snapshot / 'base-paginada' / 'indice.json'
        conteudo_indice_base = json.loads(indice_base.read_text())
        conteudo_indice_base['snapshot_id'] = 'base-paginada'
        indice_base.write_text(json.dumps(conteudo_indice_base), encoding='utf-8')
        shutil.copytree(self.snapshots / 'contrato-temporal', destino_snapshot / 'contrato-temporal')
        declaracao = ({
            'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas',
            'snapshot': 'contrato-temporal', 'diretorio': 'emissions/prospectivo-contrato',
            'modo': 'PROSPECTIVO',
        },)
        registro = registro_emissoes.validar_declaracoes(self.root, declaracao)
        self.assertEqual(registro[(2026, 18, 'americas')]['snapshot'], 'contrato-temporal')
        identificacao = self.root / 'data' / 'preparado' / 'identificacao.csv'
        identificacao.parent.mkdir(parents=True, exist_ok=True)
        identificacao.write_text('temporada,rodada,piloto_id,piloto,equipe_id_entrada,equipe_id\n', encoding='utf-8')
        asset_path = self.root / 'frontend_assets' / 'race_weekend.json'
        fontes_snapshot_original = preparar._fontes_snapshot
        with patch.object(preparar, 'SNAPSHOT_2026', 'base-paginada'), \
             patch.object(preparar, '_fontes_snapshot', side_effect=lambda root, nome='base-paginada': fontes_snapshot_original(root, 'base-paginada' if nome == preparar.SNAPSHOT_2026 else nome)), \
             patch.object(preparar, 'carregar_temporada', return_value={'previsoes': []}), \
             patch.object(preparar, '_campeonato_pilotos_2026', return_value=({'disponivel': False, 'motivo': 'fixture', 'classificacao': []}, [])), \
             patch.object(registro_emissoes, 'DECLARACOES', declaracao):
            asset = preparar.gerar(self.root, asset_path)
        carregado = race_weekend_dados.carregar_asset(self.root)
        pacote = race_weekend_dados.pacote_2026(carregado)
        corrida = next(item for item in pacote['corridas'] if item['rodada'] == 18)
        fontes_q = sorted(registro[(2026, 18, 'americas')]['fontes_qualificacao'],
                          key=lambda fonte: fonte['parametros']['offset'])
        self.assertEqual(asset['proveniencia']['emissoes']['2026:18:americas']['fonte_qualificacao_sha256'],
                         fontes_q[0]['sha256'])
        self.assertEqual(asset['proveniencia']['emissoes']['2026:18:americas']['fontes_qualificacao_sha256'],
                         [fonte['sha256'] for fonte in fontes_q])
        self.assertEqual(corrida['estado_previsao'], 'previsao_registrada')
        self.assertEqual(corrida['estado_resultado'], 'indisponivel')
        self.assertTrue(all(item['resultado_observado'] is None for item in pacote['participantes_por_rodada'][18]))
        for origem_relativa in ('reports/modelo_v1', 'reports/avaliacao_final_v1'):
            origem, destino = RAIZ / origem_relativa, self.root / origem_relativa
            destino.mkdir(parents=True, exist_ok=True)
            for arquivo in origem.iterdir():
                if arquivo.name in {'previsoes_validacao.csv', 'avaliacao_corridas.csv', 'metricas.json',
                                    'calibracao.csv', 'previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv'}:
                    shutil.copy2(arquivo, destino / arquivo.name)
        shutil.copy2(RAIZ / 'frontend_assets' / 'contexto_editorial.json',
                     self.root / 'frontend_assets' / 'contexto_editorial.json')
        shutil.copytree(RAIZ / 'dashboard_assets' / 'circuit', self.root / 'dashboard_assets' / 'circuit')
        with patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(self.root)}, clear=False):
            at = AppTest.from_file(RAIZ / 'app.py', default_timeout=15)
            at.run(timeout=15)
        self.assertFalse(at.exception, [str(item.value) for item in at.exception])

    def test_writer_recusa_prospectivo_sem_callback(self):
        with self.assertRaisesRegex(ValueError, 'tempo real'):
            previsao.gravar_emissao(self.emissions, 'sem-callback', {'modo': 'PROSPECTIVO', 'linhas': []})
        self.assertFalse((self.emissions / 'sem-callback').exists())

    def test_cli_revalida_serializacao_escrita_e_replace_e_preserva_id_existente(self):
        self._historico_real()
        self._snapshot('publicacao', include_2026_history=True)
        baseline, output, crossed, _ = self._run_cli('publicacao', 'id-existente')
        self.assertEqual(baseline, 0, output)
        self.assertFalse(crossed)
        folder = self.emissions / 'id-existente'
        before = {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in folder.rglob('*') if path.is_file()}
        repeated, output, _, _ = self._run_cli('publicacao', 'id-existente')
        self.assertEqual(repeated, 1)
        self.assertIn('já existe', output)
        after = {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in folder.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        for phase in ('serializacao', 'escrita', 'replace'):
            emission_id = 'cruza-{}'.format(phase)
            code, output, crossed, _ = self._run_cli('publicacao', emission_id, phase=phase)
            self.assertTrue(crossed)
            self.assertEqual(code, 1, '{}: {}'.format(phase, output))
            self.assertIn('largada', output)
            self.assertFalse((self.emissions / emission_id).exists())
            partials = list(self.emissions.glob('.parcial-invalida-{}-*'.format(emission_id)))
            if phase == 'replace':
                self.assertEqual(len(partials), 1)
            else:
                self.assertEqual(partials, [])


if __name__ == '__main__':
    unittest.main()
