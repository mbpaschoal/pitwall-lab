"""Exercise upcoming Mexico without inventing observed session data."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class WeekendUITests(unittest.TestCase):
    def test_practice_tyres_are_separate_from_race_and_review_is_bilingual(self):
        for lang,origin,age in [('pt','Origem do composto','Idade inicial do pneu'),('en','Compound provenance','Initial tyre age')]:
            with self.subTest(language=lang):
                root=Path(__file__).resolve().parents[1]
                script='from pitwall.i18n import set_language\nfrom pitwall.dashboard.weekend_views import load_status,render_strategies\nset_language('+repr(lang)+')\nrender_strategies(load_status('+repr(str(root))+',2026,19,"rodriguez"))'
                app=AppTest.from_string(script,default_timeout=30).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox[0].value,'Race')
                self.assertEqual(len(app.dataframe[-1].value),67)
                app.selectbox[0].select('Practice 3').run()
                self.assertFalse(app.exception)
                frame=app.dataframe[0].value
                driver='Piloto' if lang=='pt' else 'Driver'
                first=frame[(frame[driver]=='Liam LAWSON') & (frame['Stint']==1)].iloc[0]
                self.assertEqual(first['Composto' if lang=='pt' else 'Compound'],'MEDIUM')
                self.assertEqual(first[origin],'Conferência documental' if lang=='pt' else 'Documentary review')
                self.assertTrue(__import__('pandas').isna(first[age]))
                self.assertEqual(len(app.dataframe[-1].value),88)
                markdown=' '.join(item.value for item in app.markdown)
                self.assertIn('gp-tempo.com/api/laps',markdown)
                self.assertIn('thirdpracticesessionontrackanalysis',markdown)
                captions=' '.join(item.value for item in app.caption)
                self.assertIn('reconstruída por continuidade' if lang=='pt' else 'reconstructed by continuity',captions)
                app.selectbox[0].select('Race').run()
                self.assertEqual(len(app.dataframe[-1].value),67)

    def test_missing_profile_reason_is_visible_in_both_languages(self):
        state=dict(atualizado_em_utc='2026-11-01T05:00:00Z',sessoes=[dict(nome='Practice 3',estado='parcial',motivo_parcial='Cadastro de piloto ausente na fonte.')])
        for lang,column,reason in [('pt','Detalhes','Cadastro de piloto ausente na fonte.'),('en','Details','Driver profile missing from the source.')]:
            script='from pitwall.i18n import set_language\nfrom pitwall.dashboard.weekend_views import render_status\nset_language('+repr(lang)+')\nrender_status('+repr(state)+')'
            app=AppTest.from_string(script,default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.dataframe[0].value[column].tolist(),[reason])

    def test_upcoming_mexico_in_both_languages(self):
        for language, column in [('pt', 'Sessão'), ('en', 'Session')]:
            with self.subTest(language=language):
                app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40)
                app.query_params.update(dict(tela='Corridas',gp='2026:19',lang=language))
                app.run()
                self.assertFalse(app.exception)
                tables=[item.value for item in app.dataframe if column in item.value.columns]
                self.assertEqual(len(tables),1)
                self.assertEqual(len(tables[0]),5)
                self.assertTrue(any('UTC' in caption.value for caption in app.caption))


if __name__=='__main__':unittest.main()
