"""Testes sem rede da etapa 2; usam cópias das respostas reais da etapa 1."""
import copy
import importlib
import importlib.util
import io
import json
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


class TestTemporada(unittest.TestCase):
    def setUp(self):
        self.calendario = json.loads((RAIZ / 'data/raw/calendario_2024.json').read_bytes())
        self.resultados = json.loads((RAIZ / 'data/raw/resultados_sao_paulo_2024.json').read_bytes())

    def modulo(self):
        self.assertIsNotNone(importlib.util.find_spec('coletar_temporada'), 'Falta implementar o coletor da temporada')
        return importlib.import_module('coletar_temporada')

    def linhas_sp(self):
        calendario = [r for r in self.calendario['MRData']['RaceTable']['Races'] if r['round'] == '21']
        return self.modulo().montar_base(calendario, [self.resultados['MRData']['RaceTable']['Races'][0]], 20)[0]

    def test_media_indefinida_nao_e_exibida_como_zero(self):
        analise = importlib.import_module('analisar_temporada')
        self.assertEqual(analise.formatar_media(None), 'n/d')
        self.assertEqual(analise.formatar_media(0), '0.00')
        self.assertEqual(analise.formatar_media(2), '2.00')

    def test_completude_recusa_corrida_ausente(self):
        with self.assertRaisesRegex(ValueError, 'incompleta'):
            self.modulo().montar_base(self.calendario['MRData']['RaceTable']['Races'], self.resultados['MRData']['RaceTable']['Races'], 20)

    def test_duplicacao_temporada_rodada_piloto_e_recusada(self):
        corrida = copy.deepcopy(self.resultados['MRData']['RaceTable']['Races'][0])
        corrida['Results'].append(copy.deepcopy(corrida['Results'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicação'):
            self.modulo().montar_base([corrida], [corrida], 21)

    def test_podio_precisa_de_tres_posicoes_unicas(self):
        corrida = copy.deepcopy(self.resultados['MRData']['RaceTable']['Races'][0])
        corrida['Results'] = [r for r in corrida['Results'] if r['position'] != '3']
        with self.assertRaisesRegex(ValueError, 'pódio'):
            self.modulo().montar_base([corrida], [corrida], 19)

    def test_numero_de_registros_nao_e_fixado_em_vinte(self):
        pagina = json.loads((RAIZ / 'data/temporada_2024/raw/resultados_offset_0000.json').read_bytes())
        australia = [r for r in pagina['MRData']['RaceTable']['Races'] if r['round'] == '3'][0]
        linhas, resumo = self.modulo().montar_base([australia], [australia], len(australia['Results']))
        self.assertEqual(len(linhas), 19)
        self.assertEqual(resumo['registros_por_corrida'][0]['podios'], 3)

    def test_indicador_podio_depende_so_da_posicao_final(self):
        linhas = self.linhas_sp()
        for r in linhas:
            self.assertEqual(r['podio'], '1' if int(r['posicao_final']) in (1, 2, 3) else '0')
        self.assertEqual(len(linhas), 20)
        self.assertTrue(any(r['status'] == 'Did not start' for r in linhas))
        self.assertTrue(any(r['status'] == 'Disqualified' for r in linhas))

    def test_tres_acertos_ignoram_a_ordem(self):
        analise = importlib.import_module('analisar_temporada')
        linhas = self.linhas_sp()
        # Permutação controlada para testar conjuntos, não um resultado esportivo novo.
        grid = {'max_verstappen': '1', 'gasly': '2', 'ocon': '3',
                'norris': '17', 'russell': '13', 'tsunoda': '4'}
        for r in linhas:
            r['posicao_largada'] = grid.get(r['piloto_id'], r['posicao_largada'])
        self.assertEqual(analise.avaliar_corrida(linhas)['acertos'], 3)

    def test_escolha_nao_filtra_status_retrospectivamente(self):
        analise = importlib.import_module('analisar_temporada')
        linhas = self.linhas_sp()
        for r in linhas:
            if r['piloto_id'] == 'norris':
                r['status'] = 'Did not start'  # Somente cópia de teste.
        self.assertIn('norris', [r['piloto_id'] for r in analise.avaliar_corrida(linhas)['escolhidos']])

    def test_grid_top3_ausente_ou_duplicado_nao_recebe_acerto_zero_artificial(self):
        analise = importlib.import_module('analisar_temporada')
        for piloto, grid in [('norris', '0'), ('leclerc', '3')]:
            with self.subTest(piloto=piloto):
                linhas = self.linhas_sp()
                for r in linhas:
                    if r['piloto_id'] == piloto:
                        r['posicao_largada'] = grid
                a = analise.avaliar_corrida(linhas)
                self.assertFalse(a['avaliavel'])
                self.assertIsNone(a['acertos'])
                self.assertTrue(a['problemas_grid'])
                resumo = analise.resumir_analise(linhas)
                self.assertEqual(resumo['corridas_nao_avaliaveis'], 1)
                self.assertIsNone(resumo['media_acertos'])

    def test_paginas_incoerentes_nao_sao_gravadas(self):
        coleta = self.modulo()
        for alteracao in ('lista', 'offset', 'total', 'id', 'pontos'):
            pagina = copy.deepcopy(self.resultados)
            if alteracao == 'lista': pagina = []
            elif alteracao == 'offset': pagina['MRData']['offset'] = '1'
            elif alteracao == 'total': pagina['MRData']['total'] = '21'
            elif alteracao == 'id': del pagina['MRData']['RaceTable']['Races'][0]['Results'][0]['Driver']['driverId']
            else: pagina['MRData']['RaceTable']['Races'][0]['Results'][0]['points'] = 'NaN'
            with self.subTest(caso=alteracao), tempfile.TemporaryDirectory() as pasta, patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(coleta, 'urlopen', return_value=io.BytesIO(json.dumps(pagina).encode())):
                with self.assertRaises(ValueError):
                    coleta.obter_pagina('resultados', 0, Path(pasta))
                self.assertEqual(list(Path(pasta).iterdir()), [])

    def test_total_mudando_entre_paginas_e_recusado(self):
        pagina = copy.deepcopy(self.resultados)
        with self.assertRaisesRegex(ValueError, 'total mudou'):
            self.modulo().validar_pagina(pagina, 'resultados', 0, total_esperado=21)

    def test_cache_invalido_preservado_sem_consultar_rede(self):
        coleta = self.modulo()
        with tempfile.TemporaryDirectory() as pasta:
            cache = Path(pasta) / 'resultados_offset_0000.json'
            cache.write_bytes(b'[]')
            with patch.object(coleta, 'urlopen', side_effect=AssertionError('Rede proibida')) as abrir:
                with self.assertRaisesRegex(ValueError, 'Cache inválido.*backup'):
                    coleta.obter_pagina('resultados', 0, Path(pasta))
                abrir.assert_not_called()
            self.assertEqual(cache.read_bytes(), b'[]')

    def test_falha_intermediaria_nao_produz_csv_nem_comprovante(self):
        coleta = self.modulo()
        parcial = copy.deepcopy(self.resultados)
        parcial['MRData']['limit'] = '7'
        parcial['MRData']['RaceTable']['Races'][0]['Results'] = parcial['MRData']['RaceTable']['Races'][0]['Results'][:7]
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            respostas = [io.BytesIO(json.dumps(self.calendario).encode()), io.BytesIO(json.dumps(parcial).encode()), URLError('falha simulada')]
            with patch.object(coleta, 'RAIZ', pasta), patch.object(coleta, 'PASTA', pasta / 'dados'), patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(coleta.time, 'sleep'), patch.object(coleta, 'urlopen', side_effect=respostas):
                with self.assertRaises(OSError):
                    coleta.coletar()
            self.assertFalse((pasta / 'dados/resultados_2024.csv').exists())
            self.assertFalse((pasta / 'dados/verificacao.json').exists())
            self.assertTrue((pasta / 'dados/raw/resultados_offset_0000.json').exists())

    def test_http429_identificacao_e_timeout_sem_retry(self):
        coleta = self.modulo()
        erro = HTTPError(coleta.BASE_API, 429, 'Too Many Requests', {'Retry-After': '60'}, None)
        with tempfile.TemporaryDirectory() as pasta, patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(coleta, 'urlopen', side_effect=erro) as abrir:
            with self.assertRaisesRegex(ValueError, '429.*Retry-After: 60'):
                coleta.obter_pagina('resultados', 0, Path(pasta))
            abrir.assert_called_once()
            self.assertIn('PitwallLab/0.2.0', abrir.call_args.args[0].get_header('User-agent'))
            self.assertEqual(abrir.call_args.kwargs['timeout'], 30)
            self.assertEqual(list(Path(pasta).iterdir()), [])

    def test_intervalo_entre_consultas_respeita_oito_segundos(self):
        coleta = self.modulo()
        with tempfile.TemporaryDirectory() as pasta, patch.object(coleta, 'ULTIMA_REQUISICAO', 100), patch.object(coleta.time, 'monotonic', side_effect=[102, 108]), patch.object(coleta.time, 'sleep') as esperar, patch.object(coleta, 'urlopen', return_value=io.BytesIO(json.dumps(self.resultados).encode())):
            coleta.obter_pagina('resultados', 0, Path(pasta))
            esperar.assert_called_once_with(coleta.INTERVALO_SEGUNDOS - (102 - 100))
            self.assertEqual(coleta.ULTIMA_REQUISICAO, 108)

    def test_csv_alterado_ou_pagina_ausente_bloqueia_analise_sem_rede(self):
        analise = importlib.import_module('analisar_temporada')
        for caso in ('csv', 'comprovante', 'pagina'):
            with self.subTest(caso=caso), tempfile.TemporaryDirectory() as temporario:
                pasta = Path(temporario) / 'dados'
                shutil.copytree(RAIZ / 'data/temporada_2024', pasta)
                if caso == 'csv':
                    (pasta / 'resultados_2024.csv').write_bytes(b'parcial')
                elif caso == 'comprovante':
                    (pasta / 'verificacao.json').write_text('{"completa": false}')
                else:
                    (pasta / 'raw/resultados_offset_0100.json').unlink()
                with patch('coletar_temporada.urlopen', side_effect=AssertionError('Rede proibida')):
                    with self.assertRaises(ValueError):
                        analise.carregar_base(pasta)

    def test_saidas_existentes_diferentes_nao_sao_sobrescritas(self):
        coleta = self.modulo()
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario) / 'dados'
            shutil.copytree(RAIZ / 'data/temporada_2024', pasta)
            (pasta / 'resultados_2024.csv').write_bytes(b'preservar este conteudo')
            antes = {p.relative_to(pasta): p.read_bytes() for p in pasta.rglob('*') if p.is_file()}
            with patch.object(coleta, 'PASTA', pasta), patch.object(coleta, 'urlopen', side_effect=AssertionError('Rede proibida')):
                with self.assertRaises(FileExistsError):
                    coleta.coletar()
            self.assertEqual(antes, {p.relative_to(pasta): p.read_bytes() for p in pasta.rglob('*') if p.is_file()})

    def test_relatorio_distingue_referencia_retrospectiva_de_previsao_pos_classificacao(self):
        texto = (RAIZ / 'reports/temporada_2024/relatorio.md').read_text(encoding='utf-8')
        for trecho in ['### Referência retrospectiva versus previsão após a classificação',
                       'instante de corte', 'recalcular a regra simples',
                       'não são uma medição de previsões pós-classificação']:
            self.assertTrue(trecho in texto, 'Falta explicitar no relatório: ' + trecho)

    def test_relatorio_reproduzivel_sem_rede(self):
        self.modulo()
        analise = importlib.import_module('analisar_temporada')
        self.assertTrue(hasattr(analise, 'gerar'), 'Falta gerar o relatório da etapa 2')
        with tempfile.TemporaryDirectory() as pasta, patch('coletar_temporada.urlopen', side_effect=AssertionError('Rede proibida')):
            analise.gerar(saida=Path(pasta))
            esperados = {'relatorio.md', 'resumo.json', 'frequencia_grid.csv', 'avaliacao_por_corrida.csv',
                         'frequencia_grid.svg', 'acertos_por_corrida.svg', 'distribuicao_acertos.svg', 'previa.html'}
            self.assertEqual({p.name for p in Path(pasta).iterdir()}, esperados)
            antes = {p.name: p.read_bytes() for p in Path(pasta).iterdir()}
            self.assertEqual(antes, {nome: (RAIZ / 'reports/temporada_2024' / nome).read_bytes() for nome in esperados})
            analise.gerar(saida=Path(pasta))
            self.assertEqual(antes, {p.name: p.read_bytes() for p in Path(pasta).iterdir()})

    def test_resumo_mostra_contagens_e_separa_grid_zero(self):
        coleta = self.modulo()
        analise = importlib.import_module('analisar_temporada')
        corrida = self.resultados['MRData']['RaceTable']['Races'][0]
        calendario_sp = [r for r in self.calendario['MRData']['RaceTable']['Races'] if r['round'] == '21']
        linhas, _ = coleta.montar_base(calendario_sp, [corrida], 20)
        linhas[-1]['posicao_largada'] = '0'  # Cópia de teste, sem alterar o arquivo real.
        resumo = analise.resumir_analise(linhas)
        self.assertEqual(resumo['corridas_avaliaveis'], 1)
        self.assertEqual(resumo['total_podios'], 3)
        self.assertEqual(resumo['podios_top3_grid'], 0)
        self.assertEqual(resumo['media_acertos'], 0)
        self.assertEqual(resumo['distribuicao_acertos'], {'0': 1, '1': 0, '2': 0, '3': 0})
        zero = [r for r in resumo['frequencia_grid'] if r['grid'] == 0][0]
        self.assertEqual((zero['registros'], zero['podios'], zero['proporcao']), (1, 0, 0))

    def test_regra_top3_escolhe_so_pelo_grid_e_ignora_ordem_do_podio(self):
        coleta = self.modulo()
        self.assertIsNotNone(importlib.util.find_spec('analisar_temporada'), 'Falta implementar a análise')
        analise = importlib.import_module('analisar_temporada')
        corrida = self.resultados['MRData']['RaceTable']['Races'][0]
        calendario_sp = [r for r in self.calendario['MRData']['RaceTable']['Races'] if r['round'] == '21']
        linhas, _ = coleta.montar_base(calendario_sp, [corrida], 20)
        avaliacao = analise.avaliar_corrida(linhas)
        self.assertTrue(avaliacao['avaliavel'])
        self.assertEqual(avaliacao['acertos'], 0)
        self.assertEqual([r['piloto_id'] for r in avaliacao['escolhidos']], ['norris', 'russell', 'tsunoda'])
        self.assertEqual({r['piloto_id'] for r in avaliacao['podio_real']}, {'max_verstappen', 'ocon', 'gasly'})

    def test_paginacao_reune_uma_corrida_dividida_em_varias_paginas(self):
        coleta = self.modulo()
        paginas = []
        for offset in (0, 7, 14):
            pagina = copy.deepcopy(self.resultados)
            pagina['MRData']['limit'] = '7'
            pagina['MRData']['offset'] = str(offset)
            pagina['MRData']['RaceTable']['Races'][0]['Results'] = self.resultados['MRData']['RaceTable']['Races'][0]['Results'][offset:offset + 7]
            paginas.append(io.BytesIO(json.dumps(pagina).encode()))
        with tempfile.TemporaryDirectory() as pasta, patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
            coleta, 'urlopen', side_effect=paginas,
        ) as abrir, patch.object(coleta.time, 'sleep'):
            fragmentos, total = coleta.coletar_paginas('resultados', Path(pasta))
            calendario_sp = [r for r in self.calendario['MRData']['RaceTable']['Races'] if r['round'] == '21']
            linhas, resumo = coleta.montar_base(calendario_sp, fragmentos, total)
            self.assertEqual(len(linhas), 20)
            self.assertEqual(sum(int(r['podio']) for r in linhas), 3)
            self.assertEqual(resumo['corridas_coletadas'], 1)
            self.assertEqual(abrir.call_count, 3)
            self.assertEqual(len(list(Path(pasta).glob('*.json'))), 3)
            self.assertEqual([int(r['posicao_final']) for r in linhas], list(range(1, 21)))

    def test_pagina_parcial_valida_nao_exige_temporada_inteira(self):
        coleta = self.modulo()
        pagina = copy.deepcopy(self.resultados)
        pagina['MRData']['limit'] = '7'
        pagina['MRData']['RaceTable']['Races'][0]['Results'] = pagina['MRData']['RaceTable']['Races'][0]['Results'][:7]
        self.assertEqual(coleta.validar_pagina(pagina, 'resultados', 0), (20, 7))


if __name__ == '__main__':
    unittest.main()
