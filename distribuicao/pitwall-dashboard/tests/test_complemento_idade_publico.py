"""Contraprova portátil das correções de idade, sem raw, modelo ou rede."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from acervo_dashboard_dados import ASSET, carregar, conteudo_sha256


RAIZ = Path(__file__).resolve().parents[1]
COMPLEMENTO = 'frontend_assets/complemento_idade_pneus_v1.json'


def diferencas(original, atual, caminho=()):
    """Confronta a árvore inteira, inclusive chaves adicionadas/removidas."""
    if type(original) is not type(atual):
        yield caminho, original, atual
    elif isinstance(original, dict):
        if original.keys() != atual.keys():
            yield caminho, sorted(original), sorted(atual)
            return
        for chave in original:
            yield from diferencas(original[chave], atual[chave], caminho + (chave,))
    elif isinstance(original, list):
        if len(original) != len(atual):
            yield caminho, len(original), len(atual)
            return
        for i, (antes, depois) in enumerate(zip(original, atual)):
            yield from diferencas(antes, depois, caminho + (i,))
    elif original != atual:
        yield caminho, original, atual


class TestComplementoIdadePublico(unittest.TestCase):
    def test_complemento_muda_somente_262_idades_preservando_base(self):
        caminho = RAIZ / ASSET
        bytes_antes = caminho.read_bytes()
        base = json.loads(bytes_antes)
        with patch('urllib.request.urlopen', side_effect=AssertionError('Rede proibida')):
            atual = carregar(RAIZ)
        from pitwall.data.complementary_sources import load_projection
        expected = load_projection(RAIZ, base)
        deltas = list(diferencas(expected['gps'], atual['gps']))
        self.assertEqual(len(deltas), 262)
        self.assertTrue(all(caminho[-1] == 'idade' for caminho, _, _ in deltas))
        self.assertTrue(all(type(a) is int and type(b) is int and a >= 0 and b >= 0
                            for _, a, b in deltas))
        tipos = Counter('zero_para_positivo' if a == 0 and b > 0 else
                        'positivo_para_zero' if a > 0 and b == 0 else
                        'positivo_para_positivo' for _, a, b in deltas)
        self.assertEqual(tipos, {'zero_para_positivo': 210,
                                'positivo_para_zero': 36,
                                'positivo_para_positivo': 16})
        self.assertEqual(caminho.read_bytes(), bytes_antes)
        self.assertEqual(base['conteudo_sha256'], conteudo_sha256(base['gps']))
        self.assertEqual(atual['conteudo_sha256'], conteudo_sha256(atual['gps']))

    def test_pacote_leva_somente_complemento_aprovado_e_hash_manifestado(self):
        self.assertFalse((RAIZ / 'data').exists())
        self.assertFalse((RAIZ / 'models').exists())
        manifest = json.loads((RAIZ / 'MANIFESTO.json').read_text())
        indexed = {row['caminho']: row for row in manifest['arquivos']}
        for name in (COMPLEMENTO, 'pitwall/data/tyre_age.py',
                     'tests/test_complemento_idade_publico.py'):
            self.assertIn(name, indexed)
            actual_hash = hashlib.sha256((RAIZ / name).read_bytes()).hexdigest()
            self.assertEqual(indexed[name]['sha256_destino'], actual_hash)
        self.assertNotIn('/Users/', (RAIZ / COMPLEMENTO).read_text())


if __name__ == '__main__':
    unittest.main()
