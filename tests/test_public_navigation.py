"""Frame navigation must retain the same route in the hosting URL."""
import unittest
from types import SimpleNamespace
from pitwall.dashboard.journey import sync_host_query


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
