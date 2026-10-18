"""Regressões TDD do relato de desempates; usa somente registros simulados."""
import importlib
import math
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def registro(piloto_id, posicao, podio=0):
    return {
        'temporada': 2024,
        'rodada': 1,
        'piloto_id': piloto_id,
        'elegivel_previsao': True,
        'probabilidade_modelo': {'a': 0.9, 'b': 0.8, 'c': 0.7, 'd': 0.6, 'e': 0.5}[piloto_id],
        'posicao_classificacao': posicao,
        'podio': podio,
    }


def classificar(registros):
    modulo = importlib.import_module('treinar_modelo_v1')
    copia = [dict(registro) for registro in registros]
    modulo.classificar_previsoes(copia)
    return {registro['piloto_id']: registro for registro in copia}


class TestDesempatesModeloV1(unittest.TestCase):
    def test_empate_inteiramente_no_top_3_nao_afeta_fronteira(self):
        saida = classificar([
            registro('a', 1), registro('b', 2), registro('c', 2), registro('d', 4),
        ])
        self.assertEqual(saida['b']['empates_classificacao'],
                         'posicao=2:b,c; impacto_fronteira=nao')
        self.assertEqual([piloto for piloto, linha in saida.items()
                          if linha['favorito_classificacao']], ['a', 'b', 'c'])

    def test_empate_entre_terceiro_e_quarto_afeta_fronteira(self):
        saida = classificar([
            registro('a', 1), registro('b', 2), registro('c', 3), registro('d', 3),
        ])
        self.assertEqual(saida['c']['empates_classificacao'],
                         'posicao=3:c,d; impacto_fronteira=sim')

    def test_ausentes_compartilham_prioridade_e_cruzam_fronteira(self):
        saida = classificar([
            registro('a', 1), registro('b', 2),
            registro('c', math.nan), registro('d', math.nan),
        ])
        self.assertEqual(saida['c']['empates_classificacao'],
                         'posicao=ausente:c,d; impacto_fronteira=sim')
        self.assertEqual([piloto for piloto, linha in saida.items()
                          if linha['favorito_classificacao']], ['a', 'b', 'c'])

    def test_ausentes_fora_do_top_3_nao_afetam_fronteira(self):
        saida = classificar([
            registro('a', 1), registro('b', 2), registro('c', 3),
            registro('d', math.nan), registro('e', math.nan),
        ])
        self.assertEqual(saida['d']['empates_classificacao'],
                         'posicao=ausente:d,e; impacto_fronteira=nao')

    def test_favoritos_ignoram_alvo_e_auditoria_simulados(self):
        original = [
            registro('a', 1, podio=0), registro('b', 2, podio=0),
            registro('c', math.nan, podio=0), registro('d', math.nan, podio=0),
        ]
        alterado = [dict(linha, podio=1 - linha['podio'],
                         resultado_ausente=True, pontos=999, status='auditoria')
                    for linha in original]
        antes = classificar(original)
        depois = classificar(alterado)
        campos = ('ranking_classificacao', 'favorito_classificacao', 'empates_classificacao')
        self.assertEqual(
            {piloto: tuple(linha[campo] for campo in campos) for piloto, linha in antes.items()},
            {piloto: tuple(linha[campo] for campo in campos) for piloto, linha in depois.items()},
        )


if __name__ == '__main__':
    unittest.main()
