import copy
import tempfile
from pathlib import Path
import unittest
from pitwall.research import qualifying_gaps_miami as m


def fixture():
    records={};rows=['<table><tr>'+''.join('<th>'+s+'</th>' for s in ['Pos.','No.','Driver','Team','Q1','Q2','Q3','Laps'])+'</tr>']
    for i in range(20):
        driver='d'+str(i);code='D'+str(i).zfill(2);number=str(i+1);position=str(i+1)
        records[driver]={'number':number,'position':position,'Driver':{'code':code},'Constructor':{'constructorId':'mclaren'},'Q1':'','Q2':'','Q3':''}
        cells=[position,number,'Driver '+code,'McLaren','1:20.000','1:21.000' if i<15 else '', '1:22.000' if i<10 else '', '10']
        rows.append('<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>')
    return ''.join(rows)+'</table>',records


class MiamiTest(unittest.TestCase):
    def test_exact_identity_times_and_originals_preserved(self):
        html,raw=fixture();before=copy.deepcopy(raw);merged,changes=m.reconcile(html,raw)
        self.assertEqual(raw,before);self.assertEqual(len(changes),45);self.assertEqual(merged['d0']['Q1'],'1:20.000');self.assertEqual(merged['d19']['Q2'],'')
    def test_number_only_does_not_resolve_driver_team_position_conflict(self):
        for field in ('code','team','position'):
            html,raw=fixture()
            if field=='code':raw['d0']['Driver']['code']='BAD'
            if field=='team':raw['d0']['Constructor']['constructorId']='ferrari'
            if field=='position':raw['d0']['position']='20'
            with self.assertRaises(ValueError):m.reconcile(html,raw)
    def test_populated_contradictory_time_is_not_overwritten(self):
        html,raw=fixture();raw['d0']['Q1']='1:19.000'
        with self.assertRaises(ValueError):m.reconcile(html,raw)
    def test_incomplete_ambiguous_or_wrong_schema_is_not_admitted(self):
        html,raw=fixture();small=dict(list(raw.items())[:-1])
        with self.assertRaises(ValueError):m.reconcile(html,small)
        raw['d1']['number']='1'
        with self.assertRaises(ValueError):m.reconcile(html,raw)
        with self.assertRaises(ValueError):m.reconcile('<table></table>',raw)
    def test_no_source_destination_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):m.run(td,Path(td))


if __name__=='__main__':unittest.main()
