"""O pacote público leva somente a projeção portátil, com ciência preservada."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from exportar_dashboard import exportar, COMMIT_BASE_PADRAO, FONTES_CIENTIFICAS


ROOT = Path(__file__).resolve().parents[1]


class TestExportarAcervo(unittest.TestCase):
    def test_exportacao_portatil_preserva_ciencia_e_confere_zip_sem_brutos(self):
        with tempfile.TemporaryDirectory(dir=str(Path(tempfile.gettempdir()).resolve())) as temporary:
            destination = Path(temporary) / 'pacote'
            result = exportar(ROOT, destination)
            manifest = json.loads((destination / 'MANIFESTO.json').read_text())
            self.assertEqual(manifest['commit_origem'], COMMIT_BASE_PADRAO)
            for name in ('acervo_dashboard_dados.py', 'acervo_dashboard_ui.py', 'frontend_assets/acervo_dashboard.json', 'tests/test_acervo_publico.py'):
                self.assertTrue((destination / name).is_file(), name)
            for relative in FONTES_CIENTIFICAS:
                self.assertEqual((destination / relative).read_bytes(), (ROOT / relative).read_bytes())
            names = (destination / 'ARQUIVOS_PUBLICACAO.txt').read_text().splitlines()
            self.assertFalse(any(n.startswith(('data/', 'models/', 'notes/', 'projects/')) for n in names))
            self.assertFalse(any(n.startswith(('coletar_', 'preparar_acervo_')) for n in names))
            with zipfile.ZipFile(result['zip']) as archive:
                self.assertEqual(sorted(archive.namelist()), sorted(names))
                for name in names:
                    self.assertEqual(hashlib.sha256(archive.read(name)).digest(), hashlib.sha256((destination / name).read_bytes()).digest())
            self.assertTrue(exportar(ROOT, destination)['idempotente'])
