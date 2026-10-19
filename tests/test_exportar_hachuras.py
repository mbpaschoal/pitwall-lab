"""TDD da etapa 7: hachuras visíveis somente no app gerado."""
import ast
import importlib.util
import subprocess
import unittest
from pathlib import Path

import plotly.graph_objects as go


RAIZ = Path(__file__).resolve().parents[1]
BASE = '05eec0b70b24abf9a68dae45aac36730eefb5bc5'
CORES_FIXADAS = {
    'fundo': '#0D1117',
    'superficie': '#171E27',
    'texto': '#EDF0F4',
    'acento': '#E64B44',
    'modelo': '#59CDD1',
    'classificacao': '#F1AE55',
    'neutro': '#AAB5C4',
}
FIXTURE_PARTICIPANTES = [
    {'piloto_id': 'norris', 'elegivel_previsao': True, 'probabilidade_modelo': 0.31, 'favorito_modelo': True},
    {'piloto_id': 'perez', 'elegivel_previsao': True, 'probabilidade_modelo': 0.07, 'favorito_modelo': False},
    {'piloto_id': 'verstappen', 'elegivel_previsao': True, 'probabilidade_modelo': 0.42, 'favorito_modelo': True},
    {'piloto_id': 'albon', 'elegivel_previsao': True, 'probabilidade_modelo': 0.13, 'favorito_modelo': True},
]


def modulo_exportador():
    caminho = RAIZ / 'exportar_dashboard.py'
    spec = importlib.util.spec_from_file_location('exportar_dashboard_hachuras', caminho)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def fonte_app_congelada():
    resultado = subprocess.run(
        ['git', '-C', str(RAIZ), 'show', '{}:app.py'.format(BASE)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return resultado.stdout.decode('utf-8')


def grafico_da_fonte_confiavel(texto):
    arvore = ast.parse(texto)
    funcao = next(
        no for no in arvore.body
        if isinstance(no, ast.FunctionDef) and no.name == 'grafico_probabilidades'
    )
    ambiente = {'go': go, 'CORES': CORES_FIXADAS}
    exec(compile(ast.Module(body=[funcao], type_ignores=[]), '<grafico_probabilidades>', 'exec'), ambiente)
    return ambiente['grafico_probabilidades']


class TestExportarHachuras(unittest.TestCase):
    def test_app_gerado_sobrepoe_hachuras_sem_mudar_a_figura_original(self):
        fonte_original = fonte_app_congelada()
        fonte_gerada = modulo_exportador()._app_publico(fonte_original.encode('utf-8')).decode('utf-8')

        figura_original = grafico_da_fonte_confiavel(fonte_original)(FIXTURE_PARTICIPANTES)
        figura_gerada = grafico_da_fonte_confiavel(fonte_gerada)(FIXTURE_PARTICIPANTES)
        barra_original = figura_original.data[0]
        barra_gerada = figura_gerada.data[0]

        self.assertEqual(list(barra_original.x), list(barra_gerada.x))
        self.assertEqual(list(barra_original.y), list(barra_gerada.y))
        self.assertEqual(barra_original.hovertemplate, barra_gerada.hovertemplate)
        self.assertEqual(barra_original.orientation, barra_gerada.orientation)
        self.assertEqual(barra_original.name, barra_gerada.name)
        self.assertEqual(list(barra_gerada.y), ['perez', 'albon', 'norris', 'verstappen'])
        self.assertEqual(list(barra_gerada.x), [7.000000000000001, 13.0, 31.0, 42.0])
        self.assertEqual(list(barra_original.marker.pattern.shape), ['', '/', '/', '/'])
        self.assertEqual(list(barra_original.marker.color), list(barra_gerada.marker.color))
        self.assertIsNone(barra_original.marker.pattern.bgcolor)
        self.assertIsNone(barra_original.marker.pattern.fillmode)
        self.assertEqual(barra_gerada.marker.pattern.bgcolor, CORES_FIXADAS['modelo'])
        self.assertEqual(barra_gerada.marker.pattern.fillmode, 'overlay')


if __name__ == '__main__':
    unittest.main()
