"""Navigation context, forecast surprise, and immutable presentation inputs."""
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

from pitwall.dashboard.navigation import ROUTES, route_params, selected_route, search
from pitwall.dashboard.postcards import cover
from pitwall.dashboard.destination_art import DESTINATIONS
from pitwall.dashboard.tarot import deck_key, sealed_cards_html
from pitwall.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]


class ActiveText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.depth = 0
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'template':
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == 'template':
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.text.append(data)


class SidebarEditorialTests(unittest.TestCase):
    def setUp(self):
        set_language('pt')

    def test_every_route_has_one_destination_and_keeps_exact_event_context(self):
        self.assertEqual(len(ROUTES), 15)
        for key in ROUTES:
            query = route_params(key, 2024, 7, 'en')
            self.assertEqual((query['temporada'], query['gp'], query['lang']), (2024, 7, 'en'))
            self.assertEqual(selected_route(query['tela'], query), key)

    def test_fallback_retains_repeated_filters_and_clears_the_previous_destination(self):
        query = route_params('sessions', 2024, 7, 'en',
                             dict(anos=['2024', '2025'], piloto='norris',
                                  documento='metodo-v1', cartas='1', secao='termos'))
        self.assertEqual(query['anos'], ['2024', '2025'])
        self.assertEqual(query['piloto'], 'norris')
        self.assertEqual(query['aba'], 'Tempos')
        self.assertFalse({'documento', 'cartas', 'secao'} & query.keys())

    def test_search_recognizes_task_words_without_exposing_predictions(self):
        for term, expected in [('previsão', 'forecast'), ('cartas', 'forecast'),
                               ('estratégias', 'strategy'), ('voltas', 'sessions'),
                               ('duelo', 'duel'), ('construtores', 'teams-standing'),
                               ('fontes', 'sources'), ('glossário', 'terms')]:
            matches = search(term)
            self.assertIn(expected, {row['value'] for row in matches})
            self.assertTrue(all(row['kind'] == 'navigation' for row in matches))
            self.assertFalse(any('%' in row['label'] for row in matches))

    def test_sealed_faces_are_templates_not_active_names_or_probabilities(self):
        rows = [dict(driver_id='norris', name='Lando Norris', team='McLaren', probability=.682)]
        before = copy.deepcopy(rows)
        html = sealed_cards_html(rows, ROOT, 2025, 1, 'emission-a')
        text = ''.join(ActiveText(html).text)
        self.assertNotIn('Lando', text)
        self.assertNotIn('%', text)
        self.assertIn('aria-label="Revelar carta"', html)
        self.assertNotRegex(text, r'Carta\s+(?:[A-Z]|\d+)\b')
        self.assertNotIn('0 /', text)
        self.assertIn('Lando Norris', html)
        self.assertIn('68,2%', html)
        self.assertEqual(rows, before)

    def test_reveal_storage_identity_changes_with_event_emission_or_probability(self):
        rows = [dict(driver_id='norris', name='Lando Norris', team='McLaren', probability=.682)]
        base = deck_key(rows, 2025, 1, 'a')
        self.assertEqual(base, deck_key(rows, 2025, 1, 'a'))
        self.assertNotEqual(base, deck_key(rows, 2024, 1, 'a'))
        self.assertNotEqual(base, deck_key(rows, 2025, 2, 'a'))
        self.assertNotEqual(base, deck_key(rows, 2025, 1, 'b'))
        self.assertNotEqual(base, deck_key([dict(rows[0], probability=.683)], 2025, 1, 'a'))

    def test_all_current_destinations_have_local_themes_and_keep_identity(self):
        events = json.loads((ROOT / 'frontend_assets/contexto_editorial.json').read_text())['eventos']
        self.assertFalse({row['circuito_id'] for row in events} - DESTINATIONS.keys())
        for event in events:
            before = copy.deepcopy(event)
            html = cover(event, event['temporada'])
            self.assertIn(event['circuito_nome'], html)
            self.assertIn(event['data'], html)
            self.assertEqual(event, before)


if __name__ == '__main__':
    unittest.main()
