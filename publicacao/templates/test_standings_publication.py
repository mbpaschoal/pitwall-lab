"""Offline contract shared by checkout and portable distribution."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from pitwall.data.standings_state import FIELDS, MESSAGES, resolve_standings, capture_utc
from pitwall.dashboard.components import campeonatos
from pitwall.dashboard.weekend_views import load_status
from pitwall.i18n import set_language, visible_text


class TestStandingsPublication(unittest.TestCase):
    def setUp(self):
        self.identity = dict(temporada=2026, rodada=19, circuito_id='rodriguez')
        self.panels = dict(self.identity)
        self.row = dict(posicao=1, pontos=0, vitorias=0, piloto_id='test_driver',
                        piloto='Test Driver', equipe='Test Team', equipe_id='test_team')
        for field in FIELDS:
            self.panels[field] = dict(disponivel=False, classificacao=[],
                motivo='Classificação oficial desta rodada indisponível no snapshot local.')
        self.weekend = dict(self.identity, schema='pitwall-weekend-public-v1', sessoes=[],
            atualizado_em_utc='2026-11-02T00:00:00Z', campeonatos={})
        self.snapshot = dict(self.identity, disponivel=True, rodada_referencia=19,
            classificacao=[self.row], fonte='Jolpica-F1', obtido_em_utc='2026-11-01T23:45:59Z')
        self.snapshot.pop('rodada')
        self.addCleanup(set_language, 'pt')

    def unavailable(self, reason):
        return dict(disponivel=False, classificacao=[], motivo=reason)

    def test_absent_pending_failure_and_incomplete_are_distinct_and_never_zero_tables(self):
        messages = []
        for reason, status in [(None,'not_captured'), ('rodada_ainda_nao_publicada','pending'),
                ('fonte_indisponivel','source_failure'), ('Snapshot incompleto','incomplete')]:
            weekend = deepcopy(self.weekend)
            if reason:
                weekend['campeonatos'] = {f:self.unavailable(reason) for f in FIELDS}
            result = resolve_standings(self.panels, weekend)
            self.assertEqual(result[FIELDS[0]]['estado_publicacao'], status)
            html = campeonatos(result, 2026)
            self.assertNotIn('<table', html)
            self.assertEqual(html.count(MESSAGES[status]), 2)
            messages.append(MESSAGES[status])
        self.assertEqual(len(set(messages)), 4)

    def test_valid_snapshot_survives_each_failed_refresh_without_mutation(self):
        for reason in ['fonte_indisponivel','rodada_ainda_nao_publicada','incomplete /private/path']:
            panels = deepcopy(self.panels)
            panels[FIELDS[0]] = deepcopy(self.snapshot)
            self.weekend['campeonatos'][FIELDS[0]] = self.unavailable(reason)
            before = deepcopy((panels, self.weekend))
            result = resolve_standings(panels, self.weekend)
            snapshot = result[FIELDS[0]]
            self.assertEqual(snapshot['estado_publicacao'], 'cached')
            self.assertEqual(snapshot['classificacao'], [self.row])
            self.assertEqual(snapshot['obtido_em_utc'], self.snapshot['obtido_em_utc'])
            self.assertEqual((panels,self.weekend), before)
            self.assertEqual(resolve_standings(result),result)
            html = campeonatos(result,2026)
            self.assertEqual(html.count('<table'),1)
            self.assertIn(MESSAGES['cached'],html)
            self.assertNotIn('/private/path',html)

    def test_independent_published_drivers_pending_teams_and_operational_envelope(self):
        driver = deepcopy(self.snapshot)
        driver.pop('temporada'); driver.pop('circuito_id')
        self.weekend['campeonatos'] = dict(driver_standings=driver,
            constructor_standings=self.unavailable('rodada_ainda_nao_publicada'))
        result = resolve_standings(self.panels, self.weekend)
        self.assertEqual(result[FIELDS[0]]['estado_publicacao'],'published')
        self.assertEqual(result[FIELDS[1]]['estado_publicacao'],'pending')
        self.assertEqual(campeonatos(result,2026).count('<table'),1)
        self.assertEqual(resolve_standings(result),result)

    def test_explicit_round_season_circuit_and_envelope_mismatches_block_rows(self):
        for key,value in [('rodada_referencia',18),('temporada',2025),('circuito_id','americas'),('rodada_referencia','19')]:
            for operational in [False,True]:
                panels,weekend = deepcopy(self.panels),deepcopy(self.weekend)
                snapshot = dict(self.snapshot,**{key:value})
                (weekend['campeonatos'] if operational else panels)[FIELDS[0]] = snapshot
                result = resolve_standings(panels,weekend)
                self.assertEqual(result[FIELDS[0]]['estado_publicacao'],'incompatible')
                self.assertNotIn('Test Driver',campeonatos(result,2026))
                # A pre-labelled presentation state must never bypass identity.
                direct=deepcopy(panels)
                direct[FIELDS[0]]=dict(snapshot,estado_publicacao='published')
                self.assertNotIn('Test Driver',campeonatos(direct,2026))
        self.weekend.update(rodada=18,campeonatos={FIELDS[0]:self.snapshot})
        self.assertEqual(resolve_standings(self.panels,self.weekend)[FIELDS[0]]['estado_publicacao'],'incompatible')

    def test_mismatch_retains_valid_exact_event_fallback_with_warning(self):
        self.panels[FIELDS[0]]=deepcopy(self.snapshot)
        self.weekend['campeonatos'][FIELDS[0]]=dict(self.snapshot,rodada_referencia=18)
        result=resolve_standings(self.panels,self.weekend)[FIELDS[0]]
        self.assertEqual(result['estado_publicacao'],'cached')
        self.assertEqual(result['estado_consulta'],'incompatible')
        self.assertEqual(result['rodada_referencia'],19)

    def test_persisted_reader_quarantines_wrong_round_without_changing_file(self):
        self.weekend['campeonatos'][FIELDS[0]]=dict(self.snapshot,rodada_referencia=18)
        self.weekend['campeonatos'][FIELDS[1]]=deepcopy(self.snapshot)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'frontend_assets/operacao_fim_semana.json';p.parent.mkdir()
            p.write_text(json.dumps(self.weekend));before=p.read_bytes()
            state=load_status(tmp,2026,19,'rodriguez')
            self.assertFalse(state['campeonatos'][FIELDS[0]]['disponivel'])
            self.assertEqual(state['campeonatos'][FIELDS[0]]['motivo'],'evento_incompativel')
            self.assertTrue(state['campeonatos'][FIELDS[1]]['disponivel'])
            self.assertEqual(state['sessoes'],[])
            self.assertEqual(p.read_bytes(),before)

    def test_reader_checks_archived_event_snapshot_identity(self):
        archived=deepcopy(self.weekend)
        archived['campeonatos'][FIELDS[0]]=dict(self.snapshot,temporada=2025)
        current=dict(self.weekend,rodada=20,circuito_id='interlagos',arquivo_eventos=[archived])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'frontend_assets/operacao_fim_semana.json';p.parent.mkdir();p.write_text(json.dumps(current))
            state=load_status(tmp,2026,19,'rodriguez')
            self.assertEqual(state['campeonatos'][FIELDS[0]]['motivo'],'evento_incompativel')

    def test_available_empty_rows_or_missing_identity_are_incomplete(self):
        for broken in [dict(self.snapshot,classificacao=[]),dict(self.snapshot,classificacao=None),
                       {k:v for k,v in self.snapshot.items() if k!='rodada_referencia'}]:
            self.weekend['campeonatos'][FIELDS[0]]=broken
            result=resolve_standings(self.panels,self.weekend)
            self.assertEqual(result[FIELDS[0]]['estado_publicacao'],'incomplete')
            self.assertNotIn('<table',campeonatos(result,2026))

    def test_metadata_and_messages_translate_including_unknown_capture(self):
        self.weekend['campeonatos'][FIELDS[0]]=deepcopy(self.snapshot)
        result=resolve_standings(self.panels,self.weekend)
        for lang in ['pt','en']:
            set_language(lang)
            html=visible_text(campeonatos(result,2026))
            for expected in (['Fonte: Jolpica-F1','temporada 2026 · rodada 19','Captura: 2026-11-01 23:45:59 UTC'] if lang=='pt'
                             else ['Source: Jolpica-F1','season 2026 · round 19','Captured: 2026-11-01 23:45:59 UTC']):
                self.assertIn(expected,html)
            for status,message in MESSAGES.items():
                if lang=='en':self.assertNotEqual(visible_text(message),message,status)
            unknown=deepcopy(result);unknown[FIELDS[0]]['obtido_em_utc']='desconhecida'
            html=visible_text(campeonatos(unknown,2026))
            self.assertIn('Captura UTC não informada' if lang=='pt' else 'UTC capture time not reported',html)
            self.assertNotIn('2026-11-02',html)

    def test_capture_never_fabricated_from_date_or_naive_clock(self):
        for value in [None,'desconhecida','2026-11-01','2026-11-01T23:00:00','bad',12]:
            self.assertIsNone(capture_utc(dict(obtido_em_utc=value)))
        self.assertEqual(capture_utc(dict(obtido_em_utc='2026-11-01T20:00:00-03:00')),'2026-11-01 23:00:00 UTC')

    def test_untrusted_error_and_source_text_are_not_html(self):
        self.weekend['campeonatos'][FIELDS[0]]=self.unavailable('<script>secret/path</script>')
        html=campeonatos(resolve_standings(self.panels,self.weekend),2026)
        self.assertNotIn('secret/path',html)
        self.weekend['campeonatos'][FIELDS[0]]=dict(self.snapshot,fonte='<script>unsafe</script>')
        html=campeonatos(resolve_standings(self.panels,self.weekend),2026)
        self.assertNotIn('<script>',html)
