"""O exportador não modifica mais a apresentação por substituição de texto."""
import json
import tempfile
import unittest
from pathlib import Path
from exportar_dashboard import exportar, _manifesto, COMMIT_BASE_PADRAO

ROOT = Path(__file__).resolve().parents[1]


class TestComposicaoCompartilhada(unittest.TestCase):
    def test_app_e_documentacao_identicos_no_pacote(self):
        with tempfile.TemporaryDirectory(dir=str(Path(tempfile.gettempdir()).resolve())) as tmp:
            destino = Path(tmp) / 'pacote'
            exportar(ROOT, destino)
            for nome in ['app.py', 'documentacao_local.py']:
                self.assertEqual((destino / nome).read_bytes(), (ROOT / nome).read_bytes())
            from verificar_pacote import validar_pacote
            validar_pacote(destino)
            manifesto_path = destino / 'MANIFESTO.json'
            manifesto_original = manifesto_path.read_text()
            metadata = json.loads(manifesto_original)
            metadata['versao_produto'] = '999.0.0'
            manifesto_path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'Versão do produto'):
                validar_pacote(destino)
            manifesto_path.write_text(manifesto_original)
            (destino / 'extra.txt').write_text('não declarado')
            with self.assertRaisesRegex(ValueError, 'Árvore real'):
                validar_pacote(destino)
            m = json.loads((destino / 'MANIFESTO.json').read_text())
            self.assertEqual(m['baseline_cientifico_commit'], COMMIT_BASE_PADRAO)
            self.assertEqual(len(m['apresentacao_build_sha256']), 64)

    def test_mudanca_de_texto_altera_build_sem_alterar_baseline(self):
        def manifesto(conteudo):
            return _manifesto({'app.py': {'conteudo': conteudo, 'modo': 'copia',
                                         'fonte': 'app.py', 'sha256_origem': None, 'nota': None}}, ROOT, COMMIT_BASE_PADRAO)
        a, b = manifesto(b'uma interface'), manifesto(b'outro texto')
        self.assertNotEqual(a['apresentacao_build_sha256'], b['apresentacao_build_sha256'])
        self.assertEqual(a['baseline_cientifico_commit'], b['baseline_cientifico_commit'])
