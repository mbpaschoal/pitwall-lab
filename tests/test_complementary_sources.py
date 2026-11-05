"""Source admission boundaries and integration with the descriptive archive."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pitwall.data.complementary_sources import build, dump, lap, project, read, seal, sha, write_new
from pitwall.data.archive import carregar
from tests.test_acervo_dashboard_dados import asset_minimo

ROOT=Path(__file__).resolve().parents[1]


class ComplementarySources(unittest.TestCase):
    def fixture(self, root):
        def source(name,raw,url):
            (root/name).write_bytes(raw)
            return {"arquivo":name,"sha256":sha(raw),"status":200,"url":url,"obtido_em_utc":"2026-11-04T12:00:00Z"}
        memory=io.BytesIO()
        tables={"races":[{"id":1,"year":2025,"round":1,"date":"2025-03-16","circuitId":"melbourne","circuitLayoutId":"melbourne-2"}],
            "drivers":[{"id":"max-verstappen","dateOfBirth":"1997-09-30"}],
            "circuits":[{"id":"melbourne","latitude":-37.85,"longitude":144.97}],
            "races-qualifying-results":[{"raceId":1,"driverNumber":"1","driverId":"max-verstappen","positionNumber":1,"positionText":"1",
                "q1":"1:25.000","q1Millis":85000,"q2":"1:25.035","q2Millis":85035,"q3":None,"q3Millis":None}]}
        with zipfile.ZipFile(memory,"w") as z:
            for name,rows in tables.items():z.writestr("f1db-"+name+".json",dump(rows))
        f=source("f1db.zip",memory.getvalue(),"https://github.com/f1db/f1db/releases/download/v2026.19.0/f1db-json-splitted.zip");f["release"]="v2026.19.0"
        jr={"season":"2025","round":"1","date":"2025-03-16","Circuit":{"circuitId":"albert_park","Location":{"lat":"-37.85","long":"144.97"}},
            "QualifyingResults":[{"number":"1","position":"1","Driver":{"driverId":"max_verstappen","dateOfBirth":"1997-09-30"},"Q1":"1:25.000","Q2":"1:29.000","Q3":""}]}
        j=source("j.json",dump({"MRData":{"total":"1","offset":"0","RaceTable":{"Races":[jr]}}}),"https://api.jolpi.ca/ergast/f1/2025/1/qualifying.json");j.update(temporada=2025,rodada=1)
        pdf=source("proof.pdf",b"%PDF-1.7 controlled unit fixture", "https://www.fia.com/system/files/2025_australia_final_qualifying.pdf")
        plan={"schema":"pitwall-complementary-plan-v1","f1db":f,"canonical":[j],"pirelli":[],"fia_claims":[{"temporada":2025,"rodada":1,"numero":1,"field":"q2","value":"1:25.035","source":pdf,"reviewed_by":"controlled fixture review","page":2}]}
        p=root/"plan.json";p.write_bytes(dump(plan))
        return p,plan

    def asset(self):
        a=asset_minimo();gp=a['gps']['2025:1'];gp['data_corrida']='2025-03-16';s=gp['sessoes'][0];s['nome']='Qualifying';r=s['tempos'][0]
        r.update(piloto_id='max_verstappen',q1='1:25.000',q2='1:29.000',q3=None,duracao='1:29.000')
        return a

    def test_end_to_end_offline_reconciliation_and_copy_on_write(self):
        with tempfile.TemporaryDirectory() as t,patch('urllib.request.urlopen',side_effect=AssertionError('network')):
            p,_=self.fixture(Path(t));bundle=build(p);a=self.asset();old=deepcopy(a);result=project(a,bundle)
            row=result['gps']['2025:1']['sessoes'][0]['tempos'][0]
            self.assertEqual(row['q2'],'1:25.035');self.assertEqual(row['antes_complemento']['q2'],'1:29.000');self.assertEqual(a,old)
            self.assertEqual(row['duracao'],'1:25.035');self.assertIsNone(row['gap'])
            self.assertEqual(project(result,bundle),result)

    def test_unreviewed_candidate_never_overrides(self):
        with tempfile.TemporaryDirectory() as t:
            p,plan=self.fixture(Path(t));plan['fia_claims']=[];p.write_bytes(dump(plan));bundle=build(p)
            result=project(self.asset(),bundle)
            self.assertEqual(result['gps']['2025:1']['sessoes'][0]['tempos'][0]['q2'],'1:29.000')
            self.assertIsNone(bundle['events'][0]['rows'][0]['candidate']['q3'])

    def test_hash_failure_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            p,_=self.fixture(Path(t));(Path(t)/'f1db.zip').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash'):build(p)

    def test_partial_canonical_page_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p,plan=self.fixture(Path(t));j=read(Path(t)/'j.json');j['MRData']['total']='2';raw=dump(j);(Path(t)/'j.json').write_bytes(raw);plan['canonical'][0]['sha256']=sha(raw);p.write_bytes(dump(plan))
            with self.assertRaisesRegex(ValueError,'Incomplete'):build(p)

    def test_same_car_number_wrong_birthdate_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p,plan=self.fixture(Path(t));j=read(Path(t)/'j.json');j['MRData']['RaceTable']['Races'][0]['QualifyingResults'][0]['Driver']['dateOfBirth']='2000-01-01';raw=dump(j);(Path(t)/'j.json').write_bytes(raw);plan['canonical'][0]['sha256']=sha(raw);p.write_bytes(dump(plan))
            with self.assertRaisesRegex(ValueError,'birth'):build(p)

    def test_dsq_preserves_raw_and_clears_valid_display_times(self):
        with tempfile.TemporaryDirectory() as t:
            p,plan=self.fixture(Path(t));plan['fia_claims'][0].update(field='estado',value='DSQ');p.write_bytes(dump(plan));b=build(p)
            row=project(self.asset(),b)['gps']['2025:1']['sessoes'][0]['tempos'][0]
            for field in ('posicao','duracao','q1','q2','q3','gap'):self.assertIsNone(row[field])
            self.assertEqual(row['posicao_original'],'DSQ');self.assertEqual(row['antes_complemento']['q2'],'1:29.000')
            self.assertEqual(b['events'][0]['rows'][0]['candidate']['q2'],'1:25.035')

    def test_wrong_projection_event_and_driver_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p,_=self.fixture(Path(t));b=build(p);a=self.asset();a['gps']['2025:1']['identidade']['circuito_id']='other'
            with self.assertRaisesRegex(ValueError,'event identity'):project(a,b)
            a=self.asset();a['gps']['2025:1']['sessoes'][0]['tempos'][0]['piloto_id']='other'
            with self.assertRaisesRegex(ValueError,'driver identity'):project(a,b)

    def test_invalid_or_tampered_admission_rejected_even_with_new_digest(self):
        with tempfile.TemporaryDirectory() as t:
            p,_=self.fixture(Path(t));b=build(p);b['events'][0]['rows'][0]['admitted']['probabilidade']={'value':1,'reviewed_by':'x','source':{'url':'https://www.fia.com/'}};seal(b)
            with self.assertRaisesRegex(ValueError,'admitted field'):project(self.asset(),b)
            b=build(p);b['model_promotion']=True;seal(b)
            with self.assertRaisesRegex(ValueError,'scope'):project(self.asset(),b)

    def test_divergent_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'out.json';write_new(p,{'x':None});original=p.read_bytes();write_new(p,{'x':None})
            with self.assertRaises(FileExistsError):write_new(p,{'x':0})
            self.assertEqual(p.read_bytes(),original)

    def test_pinned_bundle_preserves_science_and_matches_existing_served_times(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('network')):
            b=read(ROOT/'frontend_assets/complemento_fontes_v1.json')
            original=read(ROOT/'frontend_assets/acervo_dashboard.json');a=project(original,b)
            self.assertEqual(len(b['events']),3);self.assertEqual(sum(len(e['rows']) for e in b['events']),61)
            self.assertEqual(b['pirelli'][0]['compounds'],{'HARD':'C3','MEDIUM':'C4','SOFT':'C5'})
            self.assertEqual(len(a['complemento_fontes']['aplicados']),3)
            for gp in a['gps'].values():
                for s in gp['sessoes']:
                    for r in s['tempos']:
                        if 'antes_complemento' in r:self.assertEqual(r['q2'],r['antes_complemento']['q2'])

    def test_archive_composes_pinned_tyre_revision_before_source_admission(self):
        from pitwall.data import tyre_age
        raw = (ROOT / 'frontend_assets/acervo_dashboard.json').read_bytes()
        original = json.loads(raw)
        previous_display = tyre_age.carregar(ROOT, original, raw)
        bundle = read(ROOT / 'frontend_assets/complemento_fontes_v1.json')
        expected = project(previous_display, bundle)
        from pitwall.data.identity_revision import load_projection as load_identity
        expected = load_identity(ROOT, expected)
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            actual = carregar(ROOT)
        self.assertEqual(actual, expected)
        self.assertEqual(actual['complementos_aplicados'], previous_display['complementos_aplicados'])
        self.assertEqual(sha(raw), tyre_age.BASE_SHA256)
        self.assertEqual((ROOT / 'frontend_assets/acervo_dashboard.json').read_bytes(), raw)

    def test_packaged_source_loader_is_pinned_and_rejects_symlinks(self):
        from pitwall.data.complementary_sources import ASSET, load_projection
        source = ROOT / ASSET
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / ASSET
            target.parent.mkdir()
            original = self.asset()
            self.assertIs(load_projection(temp, original), original)
            target.write_bytes(source.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'hash'):
                load_projection(temp, original)
            target.unlink()
            target.symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                load_projection(temp, original)

    def test_composition_does_not_bypass_the_original_tyre_snapshot_hash(self):
        from pitwall.data import tyre_age
        from pitwall.data.archive import AcervoDashboardErro
        from pitwall.data.complementary_sources import ASSET
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'frontend_assets').mkdir()
            base = read(ROOT / 'frontend_assets/acervo_dashboard.json')
            base['audit_unapproved'] = True
            (root / 'frontend_assets/acervo_dashboard.json').write_bytes(dump(base))
            for relative in (ASSET, tyre_age.ASSET):
                (root / relative).write_bytes((ROOT / relative).read_bytes())
            with self.assertRaisesRegex(AcervoDashboardErro, 'Base do complemento'):
                carregar(root)


if __name__=='__main__':unittest.main()
