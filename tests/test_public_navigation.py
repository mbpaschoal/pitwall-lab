"""Frame navigation must retain the same route in the hosting URL."""
import unittest
from types import SimpleNamespace
from pitwall.dashboard.journey import sync_host_query, navigation_links
from pitwall.i18n.controls import language_link, _language_params
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs))


class Query(dict):
    def __init__(self, values):
        super().__init__(values)
        self.published = []

    def get_all(self, key):
        value = self[key]
        return value if isinstance(value, list) else [value]

    def update(self, values):
        super().update(values)
        self.published.append({key: self.get_all(key)[:] for key in self})


class TestPublicNavigation(unittest.TestCase):
    def test_fallback_navigation_retains_event_language_and_repeated_filters(self):
        params = dict(temporada='2026', gp='19', faixas=['chuva', 'calor'],
                      documento='metodo', painel='pilotos', cartas='1')
        links = Links(navigation_links(params, 'Pilotos', 'en')).links
        self.assertEqual(len(links), 6)
        self.assertEqual([p['data-screen'] for p in links],
                         ['Corridas', 'Pilotos', 'Campeonato', 'Previsões', 'Desempenho', 'Metodologia'])
        for link in links:
            query = parse_qs(urlparse(link['href']).query)
            self.assertEqual(query['gp'], ['19'])
            self.assertEqual(query['temporada'], ['2026'])
            self.assertEqual(query['lang'], ['en'])
            self.assertEqual(query['faixas'], ['chuva', 'calor'])
            self.assertFalse({'documento', 'painel', 'cartas'} & query.keys())
            self.assertEqual(link['target'], '_self')
        self.assertEqual([p['data-screen'] for p in links if p.get('aria-current')], ['Pilotos'])

    def test_fallback_navigation_has_bilingual_labels_and_escapes_user_values(self):
        self.assertIn('Chances de pódio', navigation_links({}, 'Corridas'))
        html = navigation_links({'piloto': '\"><script>alert(1)</script>'}, 'Metodologia', 'en')
        self.assertIn('How it works', html)
        self.assertNotIn('<script>', html)
        self.assertEqual(len(Links(html).links), 6)

    def test_language_link_keeps_profile_duel_and_chapter_context(self):
        params = dict(temporada='2026', gp='19', tela='Pilotos', piloto='norris', rival='piastri',
                      visao='duelo', faixas=['chuva', 'calor'], aba='Clima')
        link = Links(language_link(params, 'en', 'pt')).links[0]
        query = parse_qs(urlparse(link['href']).query)
        self.assertEqual(query['lang'], ['en'])
        for key, value in params.items():
            self.assertEqual(query[key], value if isinstance(value, list) else [value])
        self.assertEqual(link['aria-label'], '🇬🇧 English')
        self.assertNotIn('aria-current', link)
        self.assertEqual(Links(language_link(params, 'pt', 'pt')).links[0]['aria-current'], 'true')
        with self.assertRaises(ValueError):
            language_link(params, 'javascript:alert(1)', 'pt')

    def test_native_and_link_language_switches_share_current_canonical_context(self):
        app = SimpleNamespace(query_params=Query({'temporada': '2025', 'gp': '2',
                                                 'faixas': ['chuva', 'calor'], 'tela': 'Pilotos'}),
                              session_state={'temporada': 2026, 'tela': 'Corridas',
                                             'gp': '2026:19', '_gp_context': '2025:2'})
        params = _language_params(app, 'Clima')
        self.assertEqual(params['temporada'], 2026)
        self.assertEqual(params['gp'], '19')
        self.assertEqual(params['tela'], 'Corridas')
        self.assertEqual(params['aba'], 'Clima')
        self.assertEqual(params['faixas'], ['chuva', 'calor'])

    def test_publish_new_route_without_losing_context_or_repeated_values(self):
        params = dict(tela='Corridas', temporada='2024', gp='2', lang='en',
                      aba='Clima', embed_options=['show_toolbar', 'show_colored_line'])
        query = Query(params)
        app = SimpleNamespace(query_params=query, session_state={})
        sync_host_query(app)
        self.assertEqual(dict(query), params)
        self.assertEqual(query.published, [{key: query.get_all(key) for key in params}])

    def test_widget_reruns_do_not_repeat_the_same_route_publication(self):
        app = SimpleNamespace(query_params=Query({'gp': '1'}), session_state={})
        sync_host_query(app)
        sync_host_query(app)
        self.assertEqual(len(app.query_params.published), 1)
        # Native callbacks already publish their changed query.
        app.query_params.update({'gp': '2'})
        sync_host_query(app)
        self.assertEqual(len(app.query_params.published), 2)
        self.assertEqual(app.query_params.published[-1]['gp'], ['2'])

    def test_html_navigation_starts_a_new_session_and_publishes_its_route(self):
        first = SimpleNamespace(query_params=Query({'gp': '1'}), session_state={})
        sync_host_query(first)
        next_page = SimpleNamespace(query_params=Query({'gp': '2'}), session_state={})
        sync_host_query(next_page)
        self.assertEqual(next_page.query_params.published, [{'gp': ['2']}])


if __name__ == '__main__':
    unittest.main()
