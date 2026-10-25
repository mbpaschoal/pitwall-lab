import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / 'data/operacao_2026/formula1dashboard/austin-tempos-f1dashboard-20261025T143617Z-r2'
SCRATCH = Path.home() / '.hermes' / 'cache' / 'scratch'


class Formula1DashboardTemposTest(unittest.TestCase):
    def copiar(self):
        temporario = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        destino = Path(temporario.name) / 'f1dashboard'
        shutil.copytree(FONTE, destino)
        self.addCleanup(temporario.cleanup)
        return destino

    def rehash(self, pasta, nome):
        inventario_path = pasta / 'inventario.json'
        inventario = json.loads(inventario_path.read_text(encoding='utf-8'))
        valor = hashlib.sha256((pasta / nome).read_bytes()).hexdigest()
        for fonte in inventario['fontes']:
            if fonte['arquivo'] == nome:
                fonte['sha256'] = valor
        inventario_path.write_text(json.dumps(inventario), encoding='utf-8')

    def test_snapshot_valido_normaliza_quatro_sessoes_e_lawson_q_parcial(self):
        from operacao2026 import formula1dashboard_tempos
        dados = formula1dashboard_tempos.carregar(FONTE)
        self.assertEqual(dados['origem'], 'formula1dashboard')
        self.assertEqual(set(dados['sessoes']), {'TL1', 'TL2', 'TL3', 'Q'})
        self.assertEqual([len(dados['sessoes'][chave]['linhas']) for chave in ('TL1', 'TL2', 'TL3', 'Q')], [22, 22, 22, 22])
        q_lawson = next(item for item in dados['sessoes']['Q']['linhas'] if item['numero_carro'] == 30)
        self.assertIsNone(q_lawson['tempo'])
        self.assertEqual(q_lawson['status'], 'NOT')
        self.assertEqual(q_lawson['q1'], '1:35.662')
        self.assertEqual(q_lawson['q2'], '1:35.058')
        self.assertIsNone(q_lawson['q3'])

    def test_tl1_mantem_herta_sem_associar_tempo_ao_perez(self):
        from operacao2026 import formula1dashboard_tempos
        dados = formula1dashboard_tempos.carregar(FONTE)
        herta = next(item for item in dados['sessoes']['TL1']['linhas'] if item['numero_carro'] == 25)
        perez = next(item for item in dados['sessoes']['TL2']['linhas'] if item['numero_carro'] == 11)
        self.assertEqual((herta['piloto'], herta['papel'], herta['piloto_id']), ('Colton Herta', 'rookie_practice', None))
        self.assertEqual(perez['piloto_id'], 'perez')
        self.assertNotEqual(herta['tempo'], perez['tempo'])

    def test_rejeita_hash_alterado_ou_sessao_de_outro_evento(self):
        from operacao2026 import formula1dashboard_tempos
        pasta = self.copiar()
        resultados = pasta / 'results.json'
        dados = json.loads(resultados.read_text(encoding='utf-8'))
        dados[0]['meeting_key'] = 9999
        resultados.write_text(json.dumps(dados), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '(?i)hash'):
            formula1dashboard_tempos.carregar(pasta)
        self.rehash(pasta, 'results.json')
        with self.assertRaisesRegex(ValueError, 'evento|sessão'):
            formula1dashboard_tempos.carregar(pasta)


if __name__ == '__main__':
    unittest.main()
