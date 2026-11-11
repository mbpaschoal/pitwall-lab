import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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
        acervo = json.loads((RAIZ / 'frontend_assets/acervo_fotografico.json').read_text())
        self.assertEqual(
            {path for path in arquivos if path.startswith('static/pitwall-archive/')},
            {variant['arquivo'] for photo in acervo['fotos'].values() for variant in photo['variantes']},
        )

    def test_cartas_neutras_sao_87_caminhos_explicitos_sem_inferir_arquivos_privados(self):
        exportador = modulo()
        arquivos = set(exportador.runtime_worktree(RAIZ))
        catalogo = json.loads((RAIZ / 'dashboard_assets/tarot/catalog.json').read_text())
        self.assertEqual(len(exportador.TAROT_DRIVER_IDS), 29)
        self.assertEqual(len(exportador.TAROT_VARIANTS), 87)
        self.assertEqual(len(set(exportador.TAROT_VARIANTS)), 87)
        self.assertEqual(set(exportador.TAROT_VARIANTS), {entry['path'] for entry in catalogo['cards']})
        self.assertEqual({entry['driver_id'] for entry in catalogo['cards']}, set(exportador.TAROT_DRIVER_IDS))
        self.assertTrue(set(exportador.TAROT_VARIANTS).issubset(arquivos))
        for entry in catalogo['overrides']:
            self.assertIn(entry['path'], arquivos)
        for module in ('hero_assets.py', 'tarot_catalog.py'):
            self.assertIn('pitwall/dashboard/' + module, arquivos)
        self.assertIn('dashboard_assets/tarot/catalog.json', arquivos)
        self.assertIn('tests/test_tarot_catalog.py', arquivos)

    def test_cartas_de_equipes_sao_126_caminhos_explicitos_separados_do_arquivo_neutro(self):
        exportador = modulo()
        arquivos = set(exportador.runtime_worktree(RAIZ))
        catalogo = json.loads((RAIZ / 'dashboard_assets/tarot/catalog.json').read_text())
        self.assertEqual(len(exportador.TAROT_TEAM_PAIRS), 42)
        self.assertEqual(len(set(exportador.TAROT_TEAM_PAIRS)), 42)
        self.assertEqual(len(exportador.TAROT_TEAM_VARIANTS), 126)
        self.assertEqual(len(set(exportador.TAROT_TEAM_VARIANTS)), 126)
        self.assertEqual(set(exportador.TAROT_TEAM_VARIANTS),
                         {entry['path'] for entry in catalogo['team_cards']})
        self.assertEqual(set(exportador.TAROT_TEAM_PAIRS),
                         {(entry['driver_id'], entry['team_id']) for entry in catalogo['team_cards']})
        self.assertTrue(set(exportador.TAROT_TEAM_VARIANTS).issubset(arquivos))
        self.assertTrue(set(exportador.TAROT_VARIANTS).isdisjoint(exportador.TAROT_TEAM_VARIANTS))

    def test_fotos_e_29_retratos_referenciados_viajam_com_o_runtime(self):
        exportador = modulo()
        arquivos = set(exportador.runtime_worktree(RAIZ))
        catalogo = json.loads((RAIZ / 'dashboard_assets/fan/hero_catalog.json').read_text())
        self.assertIn('dashboard_assets/fan/hero_catalog.json', arquivos)
        self.assertIn('tests/test_high_resolution_assets.py', arquivos)
        for hero in catalogo['heroes'].values():
            self.assertIn(hero['path'], arquivos)
        retratos = {path for path in arquivos if path.startswith('dashboard_assets/fan/portraits/')}
        self.assertEqual(len(retratos), 29)
        for driver in exportador.TAROT_DRIVER_IDS:
            suffix = '.jpg' if driver == 'ryo_hirakawa' else '.png'
            self.assertIn('dashboard_assets/fan/portraits/' + driver + suffix, retratos)
        for override in catalogo['portrait_overrides'].values():
            self.assertIn('dashboard_assets/fan/' + override['file'], arquivos)

    def test_arquivos_adjacentes_nao_entram_por_glob_nem_por_recursao(self):
        exportador = modulo()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private_paths = (
                'dashboard_assets/fan/photos/private-reference.jpg',
                'dashboard_assets/tarot/variants/hamilton/pose-secret.png',
                'dashboard_assets/tarot/variants/unlisted_driver/pose-0.png',
                'dashboard_assets/tarot/teams/mclaren/norris/pose-secret.png',
                'dashboard_assets/tarot/teams/mercedes/norris/pose-0.png',
                'dashboard_assets/tarot/teams/unlisted_team/norris/pose-0.png',
                'reports/tarot_variantes_20261101/generation/hamilton-pose-0.json',
                'static/pitwall-archive/private-reference.webp',
                'notes/private.md', '.env',
            )
            for relative in private_paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'private synthetic probe')
            archive = root / 'frontend_assets/acervo_fotografico.json'
            archive.parent.mkdir()
            archive.write_text('{"schema": 1, "fotos": {}}')
            with patch.object(exportador, '_ler_catalogo_visual', return_value={'circuitos': {}}):
                arquivos = set(exportador.runtime_worktree(root))
            self.assertTrue(set(private_paths).isdisjoint(arquivos))
            self.assertTrue(set(exportador.TAROT_VARIANTS).issubset(arquivos))
            self.assertTrue(set(exportador.TAROT_TEAM_VARIANTS).issubset(arquivos))


if __name__ == '__main__':
    unittest.main()
