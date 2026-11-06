import json
from pathlib import Path
import unittest
from historico_circuito import construir_historico, para_corrida_planejada
from resolver_pendencias_dados import classificacao_html, resolver
from normalizar_voltas_fia import extrair_layout
from acervo_dashboard_dados import carregar, para_gp, conteudo_sha256, validar, AcervoDashboardErro
from pitwall_ui_dados import carregar_paineis

ROOT=Path(__file__).resolve().parents[1]


class HistoricoPistaTest(unittest.TestCase):
    def test_exclui_atual_futuro_e_outra_pista_no_mesmo_pais(self):
        alvo={'circuito_id':'a','data_corrida':'2026-10-25'}
        rows=[dict(temporada=y,rodada=r,circuito_id=c,data_corrida=d,resultados=[dict(piloto_id='x',piloto='X',posicao=p,pontos=None)])
              for y,r,c,d,p in [(2024,1,'a','2024-10-25',1),(2025,1,'a','2025-10-25',None),(2026,1,'a','2026-10-25',3),(2027,1,'a','2027-10-25',1),(2025,2,'b','2025-09-01',1)]]
        h=construir_historico(alvo,rows)
        self.assertEqual(len(h['edicoes']),2)
        p=h['pilotos'][0];self.assertEqual(p['participacoes'],2);self.assertEqual(p['posicao_media'],1)
        self.assertIsNone(p['pontos_observados'])

    def test_asset_real_austin_2026_tem_cinco_edicoes_anteriores(self):
        a=carregar(ROOT);gp=para_gp(a,2026,18,'americas');h=gp['historico_circuito']
        self.assertEqual([x['temporada'] for x in h['edicoes']],[2025,2024,2023,2022,2021])
        self.assertTrue(all(x['circuito_id']=='americas' for x in h['edicoes']))
        h['edicoes'][0]['data_corrida']='2026-10-25'
        a['gps']['2026:18']=gp;a['conteudo_sha256']=conteudo_sha256(a['gps'])
        with self.assertRaisesRegex(AcervoDashboardErro,'atual/futura'):validar(a)

    def test_madrid_primeira_edicao_sem_emprestar_barcelona(self):
        gp=para_gp(carregar(ROOT),2026,14,'madring')
        self.assertEqual(gp['historico_circuito']['edicoes'],[])

    def test_gp_futuro_exibe_passado_sem_inventar_populacao_atual(self):
        a=carregar(ROOT)
        futuro=para_corrida_planejada(a,2026,19,'rodriguez','2026-11-01')
        self.assertEqual(len(futuro['historico_circuito']['edicoes']),5)
        self.assertEqual(futuro['historico_circuito']['edicoes'][0]['temporada'],2025)
        self.assertEqual(futuro['historico']['resultados'],[])



class FontesOficiaisTest(unittest.TestCase):
    def test_dq_preservado_sem_virar_posicao_ou_zero(self):
        rows=''.join('<tr><td>{}</td><td>{}</td><td>Piloto</td><td>Equipe</td><td>1:20.000</td><td></td><td></td><td>2</td></tr>'.format('DQ' if n==1 else n,n) for n in range(1,21))
        header='<tr>'+''.join('<th>'+x+'</th>' for x in ['Pos.','No.','Driver','Team','Q1','Q2','Q3','Laps'])+'</tr>'
        data,_=classificacao_html(('<table>'+header+rows+'</table>').encode())
        self.assertEqual(data['1']['posicao_classificacao'],'DQ')
        self.assertEqual(data['1']['q2_original'],'')

    def test_pdf_oraculo_passagens_horario_nao_e_duracao(self):
        rows=extrair_layout((ROOT/'reports/resolucao_dados_20261028/baku2025_voltas_fia.txt').read_text())
        self.assertEqual(len(rows),243);self.assertEqual(sum(x['duracao_s'] is not None for x in rows),223)
        primeira=next(x for x in rows if x['driver_number']==1 and x['lap_number_fia']==1)
        ultima=next(x for x in rows if x['driver_number']==1 and x['lap_number_fia']==16)
        self.assertIsNone(primeira['duracao_s']);self.assertEqual(primeira['tempo_publicado'],'16:04:41')
        self.assertAlmostEqual(ultima['duracao_s'],101.117)

    def test_proveniencia_nao_e_herdada_por_outros_bytes(self):
        import tempfile, hashlib
        from acervo_local import proveniencia_archive
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'archive';archive.mkdir();(archive/'a.csv').write_bytes(b'origem')
            d=root/'data/acervo_historico/resolucao-20261029';d.mkdir(parents=True)
            (d/'archive_proveniencia_resolvida.json').write_text(json.dumps({'schema':'proveniencia-archive-v1','dataset_ref':'fonte-confirmada',
                'arquivos_sha256':{'a.csv':hashlib.sha256(b'origem').hexdigest()},'obtido_em_utc':'desconhecida'}))
            self.assertEqual(proveniencia_archive(root,archive)['dataset_ref'],'fonte-confirmada')
            (archive/'a.csv').write_bytes(b'outros bytes')
            self.assertNotIn('dataset_ref',proveniencia_archive(root,archive))

    def test_adjudicacao_dq_aparece_na_apresentacao_sem_numero_inventado(self):
        gp=para_gp(carregar(ROOT),2024,8,'monaco')
        q=next(s for s in gp['sessoes'] if s['nome']=='Qualifying')
        hulkenberg=next(p for p in q['tempos'] if p['numero']==27)
        self.assertIsNone(hulkenberg['posicao'])
        self.assertEqual(hulkenberg['posicao_original'],'DQ')
        self.assertIn('formula1.com',hulkenberg['fonte_validacao'])

    def test_aviso_compartilhado_nao_e_lacuna_de_limites(self):
        from resolver_pendencias_dados import csv_ler
        base=ROOT/'data/acervo_historico/coleta-20261027T230248Z/normalizado/estrategias_pneus.csv'
        rows=csv_ler(base)
        for rodada in [3,9]:
            originais=[r for r in rows if r['temporada']=='2024' and r['rodada']==str(rodada)]
            self.assertTrue(originais)
            self.assertTrue(all(r['limites_voltas_comparaveis']=='True' for r in originais))
            gp=para_gp(carregar(ROOT),2024,rodada)
            self.assertEqual(next(c for c in gp['cobertura'] if c['tipo']=='estrategias_pneus')['estado'],'disponivel')

    def test_altitude_negativa_e_drs_de_2026_nao_aplicavel(self):
        gp=para_gp(carregar(ROOT),2025,17,'baku')
        info=carregar_paineis(ROOT,2025,17,'baku')['circuit_info']
        self.assertLess(info['altitude_m'],0)
        self.assertEqual(len(gp['voltas_fia']),243)
        info=carregar_paineis(ROOT,2026,18,'americas')['circuit_info']
        self.assertFalse(info['drs_aplicavel']);self.assertIsNone(info['zonas_drs'])

    def test_todas_fichas_tem_altitude_comprimento_curvas_e_recorde_quando_documentado(self):
        from acervo_dashboard_dados import carregar
        for gp in carregar(ROOT)['gps'].values():
            i=gp['identidade'];p=carregar_paineis(ROOT,i['temporada'],i['rodada'],i['circuito_id'])['circuit_info']
            for campo in ['comprimento_km','curvas','altitude_m','primeiro_gp','voltas','distancia_corrida_km']:
                self.assertIsNotNone(p[campo],(i,campo))
            if i['temporada']<2026:self.assertIsNotNone(p['zonas_drs'])
