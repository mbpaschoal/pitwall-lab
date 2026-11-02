"""Aceite portátil do México: leitor real, sem fontes privadas ou modelo."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from pitwall.data import post_race_evaluation as posterior
from pitwall.data.race_weekend import carregar_asset, pacote_2026

RAIZ = Path(__file__).resolve().parents[1]


class TestAvaliacaoPosteriorPublico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bytes_asset = (RAIZ / 'frontend_assets/race_weekend.json').read_bytes()
        with patch('urllib.request.urlopen', side_effect=AssertionError('Rede proibida')):
            cls.asset = carregar_asset(RAIZ)
        cls.anexo_bytes = (RAIZ / posterior.ANNEX).read_bytes()
        cls.anexo = json.loads(cls.anexo_bytes)

    def test_mexico_tem_22_alvos_e_cinco_dnf_sem_posicao_inventada(self):
        pacote = pacote_2026(self.asset)
        corrida = next(r for r in pacote['corridas'] if r['rodada'] == 19)
        self.assertEqual(corrida['circuito_id'], 'rodriguez')
        self.assertTrue(corrida['resultado_posterior_validado'])
        self.assertTrue(corrida['avaliavel_ranking'])
        self.assertEqual((corrida['acertos_modelo'], corrida['acertos_classificacao']), (2, 1))
        self.assertEqual((corrida['participantes_preparados'], corrida['elegiveis'],
                          corrida['alvos_conhecidos']), (22, 22, 22))
        linhas = pacote['participantes_por_rodada'][19]
        self.assertEqual(len({r['piloto_id'] for r in linhas}), 22)
        self.assertTrue(all(r['alvo_conhecido'] for r in linhas))
        self.assertEqual(sum(r['podio'] for r in linhas), 3)
        self.assertEqual(sorted(r['resultado_observado'] for r in linhas
                                if r['resultado_observado'] is not None), list(range(1, 18)))
        dnf = [r for r in linhas if r['resultado_observado'] is None]
        self.assertEqual(len(dnf), 5)
        self.assertTrue(all(r['status_resultado'] == 'DNF' and type(r['podio']) is int
                            and r['podio'] == 0 for r in dnf))
        self.assertEqual(sorted((r['resultado_observado'], r['piloto_id'])
                                for r in linhas if r['podio'] == 1),
                         [(1, 'max_verstappen'), (2, 'hamilton'), (3, 'antonelli')])

    def test_digest_previsao_e_anexo_vinculados_sem_fontes_privadas(self):
        self.assertFalse((RAIZ / 'data').exists())
        self.assertFalse((RAIZ / 'models').exists())
        self.assertFalse((RAIZ / 'reports/operacao_2026/emissoes').exists())
        self.assertNotIn('/Users/', self.anexo_bytes.decode())
        self.assertEqual(hashlib.sha256(self.anexo_bytes).hexdigest(), posterior.ANNEX_SHA256)
        linhas = [r for r in self.asset['dados_2026']['previsoes'] if r['rodada'] == 19]
        self.assertEqual(posterior.forecast_digest(linhas),
                         self.anexo['emissao']['projecao_previsao_sha256'])
        self.assertEqual(self.anexo['emissao']['probabilidades_sha256'],
                         'e11587ce3373cd3e9c2fa975ae11b8cd104f9e3d2842b3319f17b90c5e0d926a')
        with patch('urllib.request.urlopen', side_effect=AssertionError('Rede proibida')):
            posterior.validate_projected_asset(RAIZ, self.asset)
        self.assertEqual((RAIZ / 'frontend_assets/race_weekend.json').read_bytes(), self.bytes_asset)

    def test_alteracao_de_previsao_alvo_ou_vinculo_e_rejeitada(self):
        for caso in ('probabilidade', 'alvo', 'vinculo'):
            with self.subTest(caso=caso):
                asset = deepcopy(self.asset)
                linhas = [r for r in asset['dados_2026']['previsoes'] if r['rodada'] == 19]
                if caso == 'probabilidade':
                    linhas[0]['probabilidade_modelo'] += 0.000001
                elif caso == 'alvo':
                    next(r for r in linhas if r['resultado_observado'] is None)[
                        'podio_resultado_confirmado'] = 1
                else:
                    asset['proveniencia']['avaliacoes_posteriores'][posterior.KEY]['sha256'] = '0' * 64
                with self.assertRaises((ValueError, KeyError)):
                    posterior.validate_projected_asset(RAIZ, asset)


if __name__ == '__main__':
    unittest.main()
