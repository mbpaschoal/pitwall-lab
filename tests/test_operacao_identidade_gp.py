"""Identidade explícita, sem rede, modelo ou escrita em emissões reais."""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

import operar_2026 as cli
from tests.test_operacao_2026_integracao import corrida


class IdentidadeGPTest(unittest.TestCase):
    def test_estado_dois_gps_sem_emprestar_austin(self):
        calendar = [corrida(18, '2026-10-25', 'americas'), corrida(19, '2026-11-01', 'rodriguez')]
        with patch.object(cli, '_calendar', return_value=({'snapshot_id': 'fixture'}, calendar, {})), \
             patch.object(cli, '_selecionar_snapshot', return_value=({}, {'classificacao': []})), \
             patch.object(cli.previsao, 'carregar_modelo', side_effect=AssertionError('modelo')):
            for rodada, circuito in [(18, 'americas'), (19, 'rodriguez')]:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(cli.main(['estado', '--snapshot', 'fixture', '--temporada', '2026',
                                               '--rodada', str(rodada), '--circuito', circuito]), 0)
                self.assertEqual(json.loads(out.getvalue())['evento']['circuito_id'], circuito)
                self.assertEqual(json.loads(out.getvalue())['evento']['rodada'], str(rodada))

    def test_divergencia_falha_antes_de_abrir_classificacao(self):
        calendar = [corrida(19, '2026-11-01', 'rodriguez')]
        with patch.object(cli, '_selecionar_snapshot', side_effect=AssertionError('raw não admitido')):
            with self.assertRaisesRegex(ValueError, 'divergem'):
                cli._event_with_q('fixture', calendar, 'rodriguez', temporada='2026', rodada=18)
            with self.assertRaisesRegex(ValueError, 'divergem'):
                cli._event_with_q('fixture', calendar, 'rodriguez', temporada='2025', rodada=19)

    def test_emitir_encaminha_identidade_e_recusa_openf1_de_outro_gp(self):
        args = ['emitir', '--snapshot', 'fixture', '--temporada', '2026', '--rodada', '19',
                '--circuito', 'rodriguez', '--id', 'novo', '--sessao-encerrada-em', '2026-10-31T22:00:00Z',
                '--fonte-encerramento', 'https://example.org/q', '--corte', '2026-10-31T22:05:00Z']
        with patch.object(cli, '_preparar_fluxo', side_effect=ValueError('fixture interrompida')) as preparar, \
             redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(args), 1)
            preparar.assert_called_once_with('fixture', 'rodriguez', prospectivo=True, temporada='2026', rodada=19)
        with patch.object(cli, '_preparar_fluxo_openf1', side_effect=AssertionError('Austin indevido')), \
             redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(args + ['--openf1-diretorio', '/tmp/fixture']), 1)
