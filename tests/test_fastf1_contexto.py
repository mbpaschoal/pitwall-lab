"""Contrato offline da integração opcional FastF1 para contexto pós-sessão."""
import argparse
import hashlib
import os
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import operar_2026 as cli
from operacao2026 import fastf1_contexto as contexto


SCRATCH = Path(os.environ.get('TMPDIR') or tempfile.gettempdir())
EVENTO_AUSTIN = {
    'season': '2026', 'round': '18', 'raceName': 'United States Grand Prix',
    'date': '2026-10-25', 'Circuit': {
        'circuitId': 'americas',
        'Location': {'locality': 'Austin', 'country': 'United States'},
    },
}


class FalsaTabela:
    def to_dict(self, orient):
        assert orient == 'records'
        return [{'Abbreviation': 'VER', 'Position': 1, 'TeamName': 'Red Bull'}]


class SessaoFalsa:
    def __init__(self, nome='Practice 1', chave=981):
        self.event = {'EventName': 'United States Grand Prix', 'Location': 'Austin',
                      'Country': 'United States', 'EventDate': '2026-10-25T00:00:00'}
        self.session_info = {'Key': chave, 'Name': nome}
        self.results = FalsaTabela()
        self.loaded = None

    def load(self, **kwargs):
        self.loaded = kwargs


class DataNotLoadedError(RuntimeError):
    __module__ = 'fastf1.core'


class SessaoMetadadosIndisponiveis(SessaoFalsa):
    @property
    def session_info(self):
        raise DataNotLoadedError('Synthetic session data not available')

    @session_info.setter
    def session_info(self, value):
        pass


class FastF1Falso:
    class Cache:
        caminho = None

        @classmethod
        def enable_cache(cls, caminho):
            cls.caminho = caminho

    def __init__(self, sessao=None, erro=None):
        self.sessao, self.erro = sessao or SessaoFalsa(), erro
        self.calls = []

    def get_session(self, temporada, rodada, identificador):
        self.calls.append((temporada, rodada, identificador))
        if self.erro:
            raise self.erro
        return self.sessao


class FastF1ContextoTest(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_coleta_sessao_registra_cache_metadados_hash_e_separa_fp1_de_q(self):
        cliente = FastF1Falso()
        fp1 = contexto.coletar_sessao(
            self.root, 'austin-fp1', EVENTO_AUSTIN, 'FP1',
            modulo_fastf1=cliente, agora=datetime(2026, 10, 24, 18, tzinfo=timezone.utc),
        )
        q = contexto.coletar_sessao(
            self.root, 'austin-q', EVENTO_AUSTIN, 'Q',
            modulo_fastf1=cliente, agora=datetime(2026, 10, 24, 22, tzinfo=timezone.utc),
        )
        self.assertEqual(cliente.calls, [(2026, 18, 'FP1'), (2026, 18, 'Q')])
        self.assertEqual(FastF1Falso.Cache.caminho, str(self.root / 'cache'))
        self.assertEqual(fp1['sessao'], 'FP1')
        self.assertEqual(q['sessao'], 'Q')
        self.assertEqual(q['session_key'], '981')
        self.assertEqual(q['gp']['nome'], 'United States Grand Prix')
        self.assertEqual(q['gp']['cidade'], 'Austin')
        self.assertEqual(q['gp']['pais'], 'United States')
        self.assertEqual(q['gp']['data'], '2026-10-25')
        self.assertTrue((self.root / 'austin-q' / 'sessao.json').is_file())
        self.assertRegex(q['sha256'], r'^[0-9a-f]{64}$')
        self.assertEqual(contexto.validar_snapshot(self.root, 'austin-q')['sessao'], 'Q')

    def test_sessao_ausente_fica_aguardando_sem_falha_no_comando(self):
        texto = io.StringIO()
        with patch.object(cli, '_calendar', return_value=({'snapshot_id': 'jolpica'}, [EVENTO_AUSTIN], {})), \
             patch.object(contexto, 'coletar_sessao', side_effect=contexto.SessaoIndisponivel('FP3 ainda não publicada')):
            with redirect_stdout(texto):
                cli.cmd_coletar_fastf1(argparse.Namespace(
                    id='austin-fp3', snapshot_jolpica='jolpica', circuito='americas', sessao='FP3'))
        self.assertIn('aguardando_dados', texto.getvalue())
        self.assertIn('FP3 ainda não publicada', texto.getvalue())

    def test_data_not_loaded_em_session_info_vira_sessao_indisponivel(self):
        cliente = FastF1Falso(sessao=SessaoMetadadosIndisponiveis())
        with self.assertRaisesRegex(contexto.SessaoIndisponivel, 'ainda não está disponível'):
            contexto.coletar_sessao(self.root, 'austin-q-indisponivel', EVENTO_AUSTIN, 'Q', modulo_fastf1=cliente)
        self.assertFalse((self.root / 'austin-q-indisponivel').exists())

    def test_snapshot_fastf1_nao_substitui_q_jolpica_e_bloqueia_rodada_errada(self):
        cliente = FastF1Falso()
        contexto.coletar_sessao(self.root, 'austin-fp2', EVENTO_AUSTIN, 'FP2', modulo_fastf1=cliente)
        with self.assertRaisesRegex(ValueError, 'Q'):
            contexto.validar_contexto_emissao(self.root, 'austin-fp2', EVENTO_AUSTIN)
        evento_errado = dict(EVENTO_AUSTIN, round='17')
        with self.assertRaisesRegex(ValueError, 'rodada'):
            contexto.validar_contexto_emissao(self.root, 'austin-fp2', evento_errado, sessao_esperada='FP2')

    def test_snapshot_fastf1_rejeita_indice_cujo_gp_diverge_do_sessao_hasheado(self):
        cliente = FastF1Falso()
        contexto.coletar_sessao(self.root, 'austin-q', EVENTO_AUSTIN, 'Q', modulo_fastf1=cliente)
        pasta = self.root / 'austin-q'
        dados = json.loads((pasta / 'sessao.json').read_text(encoding='utf-8'))
        dados['gp']['rodada'] = 17
        raw = (json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
        (pasta / 'sessao.json').write_bytes(raw)
        indice = json.loads((pasta / 'indice.json').read_text(encoding='utf-8'))
        indice['sha256'] = hashlib.sha256(raw).hexdigest()
        (pasta / 'indice.json').write_text(json.dumps(indice), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'GP FastF1 divergente'):
            contexto.validar_contexto_emissao(self.root, 'austin-q', EVENTO_AUSTIN)

    def test_emissao_bloqueia_sem_classificacao_antes_de_carregar_modelo(self):
        estado = {'estado': 'aguardando_classificacao', 'registros': []}
        with patch.object(cli, '_preparar_fluxo', return_value=({}, [], EVENTO_AUSTIN, estado, {}, None, None, None)), \
             patch('operacao2026.previsao.carregar_modelo', side_effect=AssertionError('modelo não deveria carregar')):
            with self.assertRaisesRegex(ValueError, 'Aguardando classificação'):
                cli.cmd_emitir(argparse.Namespace(
                    snapshot='jolpica', id='austin-prospectivo',
                    sessao_encerrada_em='2026-10-24T22:00:00Z',
                    fonte_encerramento='https://example.test/q', corte='2026-10-24T22:01:00Z',
                    versao_anterior=None, motivo_correcao=None, fastf1_snapshot=None,
                ))


if __name__ == '__main__':
    unittest.main()
