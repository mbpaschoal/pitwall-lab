"""Verificação do acervo portátil, sem produtor, cache bruto ou rede."""
from pathlib import Path
import os
import unittest
from unittest.mock import patch
from acervo_dashboard_dados import carregar, para_gp, AcervoDashboardErro


RAIZ = Path(__file__).resolve().parents[1]


class TestAcervoPublico(unittest.TestCase):
    def test_stroll_canonical_identity_without_race_entry_or_timing_changes(self):
        import json
        base=json.loads((RAIZ/'frontend_assets/acervo_dashboard.json').read_bytes())
        current=carregar(RAIZ)
        before=base['gps']['2025:9'];after=current['gps']['2025:9']
        for s in after['sessoes']:
            rows=[r for r in s['tempos'] if r['numero']==18]
            if s['nome']=='Race':
                self.assertEqual(rows,[])
                continue
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['piloto_id'],'stroll')
            old_s=next(x for x in before['sessoes'] if x['session_key']==s['session_key'])
            old=next(r for r in old_s['tempos'] if r['numero']==18)
            self.assertIsNone(old['piloto_id'])
            self.assertEqual({k:v for k,v in rows[0].items() if k!='piloto_id'},
                             {k:v for k,v in old.items() if k!='piloto_id'})
        self.assertEqual(len(current['revisao_identidade']['aplicados']),4)

    def test_complemento_admitido_preserva_tempos_e_separa_contexto_futuro(self):
        asset = carregar(RAIZ)
        self.assertEqual(asset['cobertura']['gps'], 66)
        self.assertEqual(asset['cobertura']['sessoes'], 330)
        self.assertNotIn('2026:19', asset['gps'])
        self.assertNotIn('2026:20', asset['gps'])
        self.assertEqual(sorted(asset['complemento_fontes']['aplicados']),
                         [['2024:21', 14], ['2024:21', 23], ['2024:21', 81]])
        gp = para_gp(asset, 2024, 21, 'interlagos')
        rows = next(s['tempos'] for s in gp['sessoes'] if s['nome'] == 'Qualifying')
        expected = {14: '1:25.035', 23: '1:25.889', 81: '1:25.179'}
        for row in rows:
            if row['numero'] in expected:
                self.assertEqual(row['q2'], expected[row['numero']])
                for field, value in row['antes_complemento'].items():
                    self.assertEqual(row.get(field), value)
                self.assertIn('www.fia.com', row['fontes_por_campo']['q2']['source']['url'])
        context = asset['contextos_pirelli'][0]
        self.assertEqual((context['temporada'], context['rodada'], context['circuito_id']),
                         (2026, 20, 'interlagos'))
        self.assertEqual(context['compounds'], {'HARD': 'C3', 'MEDIUM': 'C4', 'SOFT': 'C5'})

    def test_fontes_do_gp_renderizam_em_pt_en_sem_rede(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_dashboard_app import texto_renderizado
        with patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(RAIZ)}), \
                patch('socket.create_connection', side_effect=AssertionError('network')):
            for language, label in [('pt', 'Arquivo complementar:'), ('en', 'Complementary archive:')]:
                with self.subTest(language=language):
                    app = AppTest.from_file(RAIZ / 'app.py', default_timeout=30)
                    app.query_params.update({'temporada': '2024', 'gp': '21', 'lang': language})
                    app.run(timeout=30)
                    self.assertFalse(app.exception, [str(e.value) for e in app.exception])
                    text = texto_renderizado(app)
                    self.assertIn(label, text)
                    self.assertIn('v2026.19.0', text)
                    self.assertIn('www.fia.com/sites/default/files/decision-document/', text)
                    self.assertIn('CC BY 4.0', text)
                    app.query_params.update({'temporada': '2025', 'gp': '1', 'lang': language})
                    app.run(timeout=30)
                    self.assertFalse(app.exception)
                    self.assertNotIn(label, texto_renderizado(app))

    def test_australia_tem_clima_e_sessoes_sem_precisar_do_acervo_bruto(self):
        asset = carregar(RAIZ)
        gp = para_gp(asset, 2025, 1, 'albert_park')
        self.assertTrue(gp['clima']['horas'])
        self.assertTrue(gp['sessoes'])
        self.assertTrue(gp['estrategias'])
        self.assertTrue(gp['equipes'])
        self.assertFalse((RAIZ / 'data').exists())
        self.assertFalse((RAIZ / 'models').exists())

    def test_gp_nao_empresta_dados_de_outra_temporada(self):
        asset = carregar(RAIZ)
        gp = para_gp(asset, 2026, 18, 'americas')
        self.assertEqual(gp['identidade']['temporada'], 2026)
        self.assertEqual(gp['identidade']['rodada'], 18)
        self.assertIsNone(para_gp(asset, 2026, 99))
        with self.assertRaises((ValueError, AcervoDashboardErro)):
            para_gp(asset, 2026, 18, 'monza')
