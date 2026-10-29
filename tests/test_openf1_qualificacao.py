import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

SCRATCH = Path(tempfile.gettempdir())
RAIZ = Path(__file__).resolve().parents[1]
FONTE_REAL = RAIZ / 'data' / 'operacao_2026' / 'fontes_alternativas' / 'austin-q-20261025T052624Z'


class OpenF1QualificacaoTest(unittest.TestCase):
    def copiar(self):
        temporario = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        destino = Path(temporario.name) / 'austin-q'
        shutil.copytree(FONTE_REAL, destino)
        self.addCleanup(temporario.cleanup)
        return destino

    def test_snapshot_openf1_valido_normaliza_22_ids_literais(self):
        from operacao2026 import openf1_qualificacao
        dados = openf1_qualificacao.carregar(FONTE_REAL)
        self.assertEqual(dados['origem'], 'openf1')
        self.assertEqual(dados['sessao']['session_key'], 11392)
        self.assertEqual(dados['encerramento_utc'], '2026-10-24T22:00:00.097000Z')
        self.assertEqual(len(dados['registros']), 22)
        self.assertEqual({item['Driver']['driverId'] for item in dados['registros']}, {
            'antonelli', 'max_verstappen', 'hadjar', 'leclerc', 'hamilton', 'russell',
            'piastri', 'norris', 'arvid_lindblad', 'lawson', 'gasly', 'hulkenberg',
            'bortoleto', 'colapinto', 'alonso', 'bearman', 'ocon', 'stroll', 'sainz',
            'albon', 'perez', 'bottas',
        })
        self.assertEqual(dados['registros'][0]['Driver']['driverId'], 'antonelli')
        self.assertEqual(dados['registros'][0]['Constructor']['constructorId'], 'mercedes')

    def test_rejeita_hash_alterado_e_encerramento_de_q1(self):
        from operacao2026 import openf1_qualificacao
        pasta = self.copiar()
        raw = pasta / 'openf1-austin-q-race_control.json'
        mensagens = json.loads(raw.read_text())
        for item in mensagens:
            if item.get('message') == 'SESSION FINISHED' and item.get('qualifying_phase') == 3:
                item['qualifying_phase'] = 1
        raw.write_text(json.dumps(mensagens), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '(?i)hash'):
            openf1_qualificacao.carregar(pasta)
        inventario = json.loads((pasta / 'inventario.json').read_text())
        novo_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        inventario['sha256_arquivos'][raw.name] = novo_hash
        for fonte in inventario['fontes']:
            if fonte['arquivo'] == raw.name:
                fonte['sha256'] = novo_hash
        (pasta / 'inventario.json').write_text(json.dumps(inventario), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Q3'):
            openf1_qualificacao.carregar(pasta)

    def test_rejeita_cobertura_incompleta_ou_driver_duplicado(self):
        from operacao2026 import openf1_qualificacao
        pasta = self.copiar()
        raw = pasta / 'openf1-austin-q-session_result.json'
        resultados = json.loads(raw.read_text())
        resultados[-1]['driver_number'] = resultados[-2]['driver_number']
        raw.write_text(json.dumps(resultados), encoding='utf-8')
        inventario = json.loads((pasta / 'inventario.json').read_text())
        novo_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        inventario['sha256_arquivos'][raw.name] = novo_hash
        for fonte in inventario['fontes']:
            if fonte['arquivo'] == raw.name:
                fonte['sha256'] = novo_hash
        (pasta / 'inventario.json').write_text(json.dumps(inventario), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicado'):
            openf1_qualificacao.carregar(pasta)


if __name__ == '__main__':
    unittest.main()
