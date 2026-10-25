import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import catalogo_visual


class TestCatalogoVisual(unittest.TestCase):
    def test_recusa_caminho_fora_da_raiz(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pasta = raiz / 'dashboard_assets/circuit'
            pasta.mkdir(parents=True)
            segredo = raiz.parent / 'segredo.jpg'
            segredo.write_bytes(b'segredo')
            item = {'caminho': '../segredo.jpg', 'sha256': hashlib.sha256(b'segredo').hexdigest(),
                    'autor': 'Autor', 'licenca': 'CC BY', 'pagina': 'https://exemplo.test', 'mime': 'image/jpeg'}
            (pasta / 'catalogo_visual.json').write_text(json.dumps({'versao': 1, 'circuitos': {'teste': {'foto': item, 'mapa': item}}}), encoding='utf-8')
            with self.assertRaises(catalogo_visual.CatalogoVisualErro):
                catalogo_visual.carregar(raiz)

    def test_recusa_ativo_com_hash_divergente(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pasta = raiz / 'dashboard_assets/circuit'
            pasta.mkdir(parents=True)
            (pasta / 'ativo.jpg').write_bytes(b'conteudo alterado')
            item = {'caminho': 'dashboard_assets/circuit/ativo.jpg', 'sha256': '0' * 64,
                    'autor': 'Autor', 'licenca': 'CC BY', 'pagina': 'https://exemplo.test', 'mime': 'image/jpeg'}
            (pasta / 'catalogo_visual.json').write_text(json.dumps({'versao': 1, 'circuitos': {'teste': {'foto': item, 'mapa': item}}}), encoding='utf-8')
            with self.assertRaises(catalogo_visual.CatalogoVisualErro):
                catalogo_visual.carregar(raiz)

    def test_recusa_catalogo_symlink_sem_tocar_na_sentinela(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario) / 'pacote'
            pasta = raiz / 'dashboard_assets' / 'circuit'
            pasta.mkdir(parents=True)
            sentinela = Path(temporario) / 'catalogo-sentinela.json'
            conteudo = b'{"versao": 1, "circuitos": {}}\n'
            sentinela.write_bytes(conteudo)
            antes = sentinela.stat()
            (pasta / 'catalogo_visual.json').symlink_to(sentinela)

            with self.assertRaisesRegex(catalogo_visual.CatalogoVisualErro, 'symlink'):
                catalogo_visual.carregar(raiz)

            self.assertEqual(sentinela.read_bytes(), conteudo)
            self.assertEqual(sentinela.stat().st_mtime_ns, antes.st_mtime_ns)
