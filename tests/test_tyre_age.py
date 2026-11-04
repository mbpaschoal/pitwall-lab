"""Scientific boundary and fail-closed tests for the accepted tyre-age revision."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pitwall.data.archive import ASSET as BASE, carregar, conteudo_sha256, AcervoDashboardErro
from pitwall.data import tyre_age

ROOT=Path(__file__).resolve().parents[1]

def differences(before,after,path=()):
    if type(before) is not type(after):
        yield path,before,after
    elif isinstance(before,dict):
        if before.keys()!=after.keys():
            yield path,before.keys(),after.keys()
        else:
            for k in before: yield from differences(before[k],after[k],path+(k,))
    elif isinstance(before,list):
        if len(before)!=len(after):yield path,len(before),len(after)
        else:
            for i,(a,b) in enumerate(zip(before,after)):yield from differences(a,b,path+(i,))
    elif before!=after:
        yield path,before,after

class TyreAgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/BASE).read_bytes()
        cls.base=json.loads(cls.raw)
        cls.complement=json.loads((ROOT/tyre_age.ASSET).read_bytes())

    def test_only_262_age_leaves_change_and_original_stays_intact(self):
        before=deepcopy(self.base)
        with patch('urllib.request.urlopen',side_effect=AssertionError('No network')):
            revised=carregar(ROOT)
        from pitwall.data.complementary_sources import load_projection
        expected = load_projection(ROOT, self.base)
        delta=list(differences(expected['gps'],revised['gps']))
        identity = [(p,a,b) for p,a,b in delta if p[-1]=='piloto_id']
        self.assertEqual(len(identity),4)
        self.assertTrue(all(p[0]=='2025:9' and a is None and b=='stroll' for p,a,b in identity))
        delta = [(p,a,b) for p,a,b in delta if p[-1]!='piloto_id']
        self.assertEqual(len(delta),262)
        self.assertTrue(all(p[-1]=='idade' for p,_,_ in delta))
        kinds=Counter('zero_positive' if a==0 and b>0 else 'positive_zero' if a>0 and b==0 else 'positive_positive' for _,a,b in delta)
        self.assertEqual(kinds,{'zero_positive':210,'positive_zero':36,'positive_positive':16})
        self.assertEqual(self.base,before)
        self.assertEqual((ROOT/BASE).read_bytes(),self.raw)
        self.assertEqual(revised['conteudo_sha256'],conteudo_sha256(revised['gps']))

    def test_physical_identity_and_recorded_forecasts_are_not_inputs_to_revision(self):
        self.assertNotIn('tyre_age_at_start',json.loads((ROOT/'data/preparado/colunas.json').read_text())['entradas'])
        forecasts=list((ROOT/'reports/operacao_2026/emissoes').rglob('*.csv'))
        before={p:sha256(p.read_bytes()).hexdigest() for p in forecasts}
        carregar(ROOT)
        self.assertEqual(before,{p:sha256(p.read_bytes()).hexdigest() for p in forecasts})
        self.assertTrue(forecasts)

    def test_missing_complement_never_silently_restores_old_ages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/BASE;path.parent.mkdir();path.write_bytes(self.raw)
            with self.assertRaisesRegex(AcervoDashboardErro,'obrigatório'):
                carregar(tmp)

    def test_corrupt_complement_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/BASE;path.parent.mkdir();path.write_bytes(self.raw)
            (Path(tmp)/tyre_age.ASSET).write_text('{}')
            with self.assertRaisesRegex(AcervoDashboardErro,'Hash'):
                carregar(tmp)

    def test_known_content_without_origin_still_requires_complement(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/BASE;path.parent.mkdir()
            base=deepcopy(self.base);base.pop('acervo_origem')
            path.write_text(json.dumps(base))
            with self.assertRaisesRegex(AcervoDashboardErro,'obrigatório'):
                carregar(tmp)

    def test_changed_base_rejected_even_with_updated_internal_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/BASE;path.parent.mkdir()
            base=deepcopy(self.base);base['gps']['2024:1']['aviso']='other'
            base['conteudo_sha256']=conteudo_sha256(base['gps']);path.write_text(json.dumps(base))
            shutil.copyfile(ROOT/tyre_age.ASSET,Path(tmp)/tyre_age.ASSET)
            with self.assertRaisesRegex(AcervoDashboardErro,'Base do complemento'):
                carregar(tmp)

    def test_duplicate_native_identity_rejected(self):
        data=deepcopy(self.complement);data['correcoes'][1]=deepcopy(data['correcoes'][0])
        with self.assertRaisesRegex(tyre_age.TyreAgeError,'duplicada'):
            tyre_age.aplicar(self.base,data)

    def test_wrong_gp_or_session_or_driver_rejected(self):
        for k,v in [('gp_key','2026:19'),('session_key',11404),('driver_number',999),('circuito_id','other')]:
            data=deepcopy(self.complement);data['correcoes'][0][k]=v
            with self.assertRaises(tyre_age.TyreAgeError):tyre_age.aplicar(self.base,data)

    def test_different_compound_bounds_or_old_age_rejected(self):
        for k,v in [('composto','WET'),('inicio',999),('fim',999),('idade_original',999)]:
            data=deepcopy(self.complement);data['correcoes'][0][k]=v
            with self.assertRaises(tyre_age.TyreAgeError):tyre_age.aplicar(self.base,data)

    def test_boolean_null_negative_or_string_not_accepted_as_age(self):
        for value in [False,True,None,-1,'0',0.0]:
            data=deepcopy(self.complement);data['correcoes'][0]['idade_revisada']=value
            with self.assertRaises(tyre_age.TyreAgeError):tyre_age.aplicar(self.base,data)

    def test_invalid_boolean_bounds_rejected(self):
        data=deepcopy(self.complement);data['correcoes'][0]['inicio']=True
        with self.assertRaises(tyre_age.TyreAgeError):tyre_age.aplicar(self.base,data)

    def test_omitted_or_additional_record_rejected(self):
        for n in [261,263]:
            data=deepcopy(self.complement)
            data['correcoes']=(data['correcoes']+[data['correcoes'][0]])[:n]
            with self.assertRaises(tyre_age.TyreAgeError):tyre_age.aplicar(self.base,data)

    def test_bad_result_hash_rejected_without_partial_mutation(self):
        data=deepcopy(self.complement);data['conteudo_revisado_sha256']='0'*64
        before=deepcopy(self.base)
        with self.assertRaisesRegex(tyre_age.TyreAgeError,'Resultado'):
            tyre_age.aplicar(self.base,data)
        self.assertEqual(self.base,before)

    def test_timezone_and_source_provenance_required(self):
        for k,v in [('criado_em_utc','2026-11-01T12:00:00'),('fontes',[])]:
            data=deepcopy(self.complement);data[k]=v
            with self.assertRaises(tyre_age.TyreAgeError):tyre_age.aplicar(self.base,data)

    def test_complement_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/BASE;path.parent.mkdir();path.write_bytes(self.raw)
            (Path(tmp)/tyre_age.ASSET).symlink_to(ROOT/tyre_age.ASSET)
            with self.assertRaisesRegex(AcervoDashboardErro,'symlink'):
                carregar(tmp)

if __name__=='__main__':unittest.main()
