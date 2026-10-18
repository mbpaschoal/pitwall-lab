"""TDD do SVG de calibração; usa exclusivamente linhas simuladas."""
import importlib
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def linhas_calibracao_simuladas():
    linhas = []
    valores = {
        'modelo': {
            1: (5, 0.15, 0.20),
            6: (3, 0.62, 0.67),
        },
        'constante': {
            1: (7, 0.15, 0.60),
            8: (2, 0.84, 0.50),
        },
    }
    for metodo in ('modelo', 'constante'):
        for indice in range(10):
            limite_inferior = indice / 10
            limite_superior = (indice + 1) / 10
            contagem, media, frequencia = valores[metodo].get(indice, (0, None, None))
            linhas.append({
                'metodo': metodo,
                'faixa': '[{:.1f},{:.1f}{})'.format(
                    limite_inferior, limite_superior, ']' if indice == 9 else ')'),
                'limite_inferior': limite_inferior,
                'limite_superior': limite_superior,
                'contagem': contagem,
                'media_prevista': media,
                'frequencia_observada': frequencia,
            })
    return linhas


def nome_local(elemento):
    return elemento.tag.rsplit('}', 1)[-1]


class TestCalibracaoSvg(unittest.TestCase):
    def test_pontos_usam_medias_e_frequencias_com_escala_compartilhada(self):
        modulo = importlib.import_module('treinar_modelo_v1')
        raiz = ET.fromstring(modulo._svg_calibracao(linhas_calibracao_simuladas()))
        circulos = [elemento for elemento in raiz.iter()
                    if nome_local(elemento) == 'circle' and 'data-metodo' in elemento.attrib]
        self.assertEqual(len(circulos), 4)

        por_chave = {(elemento.attrib['data-metodo'], float(elemento.attrib['data-media-prevista'])): elemento
                     for elemento in circulos}
        modelo = por_chave[('modelo', 0.15)]
        constante = por_chave[('constante', 0.15)]
        self.assertEqual(modelo.attrib['cx'], constante.attrib['cx'])

        esquerda = float(raiz.attrib['data-reliability-left'])
        largura = float(raiz.attrib['data-reliability-width'])
        base = float(raiz.attrib['data-reliability-bottom'])
        altura = float(raiz.attrib['data-reliability-height'])
        for circulo in circulos:
            media = float(circulo.attrib['data-media-prevista'])
            frequencia = float(circulo.attrib['data-frequencia'])
            self.assertAlmostEqual(float(circulo.attrib['cx']), esquerda + media * largura)
            self.assertAlmostEqual(float(circulo.attrib['cy']), base - frequencia * altura)
            self.assertTrue(any(nome_local(filho) == 'title' for filho in circulo))

    def test_faixas_vazias_nao_viram_pontos_e_contagens_ficam_auditaveis(self):
        modulo = importlib.import_module('treinar_modelo_v1')
        linhas = linhas_calibracao_simuladas()
        raiz = ET.fromstring(modulo._svg_calibracao(linhas))
        circulos = [elemento for elemento in raiz.iter()
                    if nome_local(elemento) == 'circle' and 'data-metodo' in elemento.attrib]
        barras = [elemento for elemento in raiz.iter()
                  if nome_local(elemento) == 'rect' and 'data-contagem' in elemento.attrib]

        self.assertEqual(len(circulos), sum(linha['contagem'] > 0 for linha in linhas))
        self.assertEqual(len(barras), 20)
        self.assertEqual(
            {(barra.attrib['data-metodo'], barra.attrib['data-faixa']): int(barra.attrib['data-contagem'])
             for barra in barras},
            {(linha['metodo'], linha['faixa']): linha['contagem'] for linha in linhas},
        )
        self.assertNotIn('0.0', {(circulo.attrib['data-media-prevista']) for circulo in circulos})
        textos = [''.join(elemento.itertext()) for elemento in raiz.iter() if nome_local(elemento) == 'text']
        self.assertIn('0.0', textos)
        self.assertIn('1.0', textos)


if __name__ == '__main__':
    unittest.main()
