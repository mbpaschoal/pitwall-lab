import json
import unittest
from diagnosticos_v2 import gerar_diagnosticos, intervalo_blocos
from executar_metodologia_v2 import dividir_selecao_temporal, registrar_selecao


class RastreabilidadeTest(unittest.TestCase):
    def test_2022_registra_gps_reais_e_hash_independente_da_ordem(self):
        treino = [{'temporada': 2021, 'rodada': r, 'piloto_id': 'a'} for r in range(1, 11)]
        ajuste, valid = dividir_selecao_temporal(treino)
        self.assertEqual([x['rodada'] for x in ajuste], list(range(1, 9)))
        self.assertEqual([x['rodada'] for x in valid], [9, 10])
        a = registrar_selecao(treino, 2022, 'q', 'candidato')
        b = registrar_selecao(list(reversed(treino)), 2022, 'q', 'candidato')
        self.assertEqual(a['temporadas_ajuste'], '2021')
        self.assertEqual(json.loads(a['gps_validacao_interna']), [[2021, 9], [2021, 10]])
        self.assertEqual(a['sha256_ajuste'], b['sha256_ajuste'])
        fixa = registrar_selecao(treino, 2022, 'v1', 'C1', fixa=True)
        self.assertEqual(fixa['tipo'], 'receita_fixa')
        self.assertEqual(fixa['n_validacao_interna'], 0)
        self.assertEqual(fixa['n_ajuste'], 10)

    def test_sem_particoes_validas_falha(self):
        with self.assertRaises(ValueError):
            dividir_selecao_temporal([{'temporada': 2021, 'rodada': 1}])


class DiagnosticosTest(unittest.TestCase):
    def linhas(self):
        return [dict(metodo=m, fold=ano, temporada=ano, rodada=r, piloto_id=str(i),
                     probabilidade=(.9 if i < 3 else .1) if m == 'q_a3_completo' else .5,
                     podio=int(i < 3), alvo_conhecido=1)
                for m in ['q_a3_completo', 'q_flexivel', 'v1_replicado_temporal']
                for ano in [2022, 2023, 2024, 2025] for r in [1, 2, 3] for i in range(4)]

    def test_oraculo_brier_calibracao_top3_e_ic(self):
        d = gerar_diagnosticos(self.linhas())
        r = next(x for x in d['resumos'] if x['metodo'] == 'q_a3_completo')
        self.assertAlmostEqual(r['brier_medio_gp'], .01)
        self.assertEqual(r['podios_completos'], 12)
        self.assertEqual(len(d['calibracao'][0]['faixas']), 10)
        for c in d['comparacoes']:
            self.assertAlmostEqual(c['delta_brier'], -.24)
            self.assertAlmostEqual(c['ic95_brier'][1], -.24)
            self.assertEqual(c['conclusao'], 'melhora_sustentada')
        self.assertFalse(d['promocao_automatica'])

    def test_coorte_divergente_nao_faz_intersecao_e_alvo_desconhecido_nao_e_zero(self):
        linhas = self.linhas()
        linhas[0]['alvo_conhecido'] = 0
        linhas[0]['podio'] = ''
        d = gerar_diagnosticos(linhas)
        self.assertEqual(d['comparacoes'][0]['conclusao'], 'cobertura_insuficiente')
        r = next(x for x in d['ranking_por_gp'] if x['metodo'] == 'q_a3_completo')
        self.assertIsNone(r['acertos_top3'])
        self.assertIsNone(intervalo_blocos({2022: [.1]}))

    def test_bootstrap_reprodutivel_e_sem_cruzar_temporadas(self):
        dados = {2022: [-.2, -.1, .3], 2023: [-.2, -.1]}
        self.assertEqual(intervalo_blocos(dados), intervalo_blocos(dados))
        self.assertIsNone(intervalo_blocos({2022: [.1, .2], 2023: [.1]}))

    def test_duplicata_e_2026_rejeitados(self):
        linhas = self.linhas()
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            gerar_diagnosticos(linhas + linhas[:1])
        linhas[0]['temporada'] = 2026
        with self.assertRaisesRegex(ValueError, 'retrospectivos'):
            gerar_diagnosticos(linhas)
