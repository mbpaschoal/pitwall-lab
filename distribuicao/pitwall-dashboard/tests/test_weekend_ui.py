"""Exercise upcoming Mexico without inventing observed session data."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class WeekendUITests(unittest.TestCase):
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
