import importlib.util
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def modulo():
    spec = importlib.util.spec_from_file_location('exportar_dashboard_catalogo', RAIZ / 'exportar_dashboard.py')
    assert spec and spec.loader
    resultado = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resultado)
    return resultado


class TestExportarCatalogo(unittest.TestCase):
    def test_allowlist_runtime_inclui_catalogo_e_todos_os_ativos_referenciados(self):
        exportador = modulo()
        arquivos = set(exportador.runtime_worktree(RAIZ))
        self.assertIn('contexto_editorial.py', arquivos)
        self.assertIn('catalogo_visual.py', arquivos)
        self.assertIn('registro_emissoes.py', arquivos)
        self.assertIn('frontend_assets/contexto_editorial.json', arquivos)
        self.assertIn('dashboard_assets/circuit/catalogo_visual.json', arquivos)
        catalogo = exportador._ler_catalogo_visual(RAIZ)
        self.assertEqual(len(catalogo['circuitos']), 26)
        for ativos in catalogo['circuitos'].values():
            self.assertIn(ativos['foto']['caminho'], arquivos)
            self.assertIn(ativos['mapa']['caminho'], arquivos)


if __name__ == '__main__':
    unittest.main()
